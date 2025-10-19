import time
import logging
import sys, os
import asyncio
import threading
import socket
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence
from utils.nodriverUtil import DriverController
from utils.helpers import log_line

import eel

BETWEEN_WORKERS_STAGGER_SEC = 15.0


@dataclass(frozen=True)
class Credentials:
    """User credentials (kept for parity with the original function signature)."""
    numero: Optional[str] = None
    contrasena: Optional[str] = None


@dataclass(frozen=True)
class LaunchOptions:
    """High-level options controlling how browsers are launched."""
    is_nopecha: bool = False
    is_madridista: bool = False
    is_vpn: bool = False
    browsers_amount: int = 1
    adspower_api: Optional[str] = None
    adspower_ids: Sequence[str] = field(default_factory=tuple)
    proxy_list: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class AppConfig:
    """Top-level configuration for a run."""
    initial_url: str
    credentials: Credentials
    options: LaunchOptions


# Utilities


class Ports:
    """Utility for checking port availability"""

    @staticmethod
    def is_open(host: str, port: int, timeout_sec: float = 1.0) -> bool:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout_sec)
        try:
            sock.connect((host, port))
            return True
        except (socket.timeout, ConnectionRefusedError):
            return False
        finally:
            sock.close()


def normalize_adspower_ids(adspower_ids: Iterable[str | int] | str | None) -> List[str]:
    """Accept list or multiline string; return cleaned list of strings."""
    if adspower_ids is None:
        return []
    if isinstance(adspower_ids, str):
        return [ln.strip() for ln in adspower_ids.splitlines() if ln.strip()]
    return [str(x).strip() for x in adspower_ids if str(x).strip()]


def adspower_link_for(api: Optional[str], profile_id: Optional[str]) -> Optional[str]:
    if api and profile_id:
        return f"{api}/api/v1/browser/start?serial_number={profile_id}"
    return api  # None or raw api handled by browser_connect


def chrome_profile_name(thread_index: int, adspower_id: Optional[str]) -> str:
    suffix = adspower_id if adspower_id else str(thread_index)
    return f"{os.name}_{suffix}"
# Browser orchestration & domain logic

class MainLoop:
    def __init__(self, controller: DriverController) -> None:
        self.controller = controller
        self._running = False

    async def run(self) -> None:
        self._running = True
        while self._running:
            try:
                # Iterate over a static copy of tabs to avoid mutation issues during loop
                for t in list(self.controller.driver.tabs):
                    await self.controller.recover_if_blocked(t)
                    await self.controller.reload_initial_if_home_redirect(t)
                    await self.controller.click_verify(self.controller.driver, t)

                # Small cooperative pause to avoid hot loop
                await asyncio.sleep(5)

            except Exception as exc:
                log_line("error", f"Verification loop error: {exc}")
                # Back off a bit on errors to avoid log spam and tight loops
                await asyncio.sleep(5.0)

    def stop(self) -> None:
        self._running = False


class BrowserWorker:
    """
    One autonomous browser worker. Inteded to run in its own thread.
    Creates its own asyncio event loop; does not share loop state.
    """

    def __init__(
        self,
        index: int,
        config: AppConfig,
        adspower_id: Optional[str] = None,
    ) -> None:
        self.index = index
        self.config = config
        self.adspower_id = adspower_id
        self.controller: Optional[DriverController] = None
        self.loop_task: Optional[asyncio.Task] = None

    def run(self) -> None:
        """Entry point for the thread"""
        name = f"Browser {self.adspower_id}" if self.adspower_id \
        else f"Thread {self.index}"
        log_line("success", f"{name} started")
        self._run_coroutine_in_flesh_loop(self._run_async())
        
    def _run_coroutine_in_flesh_loop(self, coro: asyncio.coroutines) -> None:
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            loop.run_until_complete(coro)
        finally:
            loop.close()
    
    async def _run_async(self) -> None:
        link = adspower_link_for(self.config.options.adspower_api, self.adspower_id)
        profile = chrome_profile_name(self.index, self.adspower_id)

        self.controller = DriverController(
            initial_url=self.config.initial_url,
            proxy_list=self.config.options.proxy_list,
            profile_name=profile,
            adspower_link=link,
        )

        await self.controller.setup_driver()
        await self.controller.post_connect_setup()
        await self.controller.navigate_initial()

        loop = MainLoop(self.controller)
        await loop.run()


class WorkersOrchestrator:
    """Creates and manages workers; provides the public 'launch' API used by the UI layer."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.threads: List[threading.Thread] = []

    def launch(self) -> None:
        """Launch workers either with AdsPower profiles or plain multi-browser run."""
        opts = self.config.options
        adspower_ids = normalize_adspower_ids(opts.adspower_ids)

        if not opts.adspower_api and not adspower_ids:
            self._launch_without_adspower()
        else:
            self._launch_with_adspower(adspower_ids)
        
        for t in self.threads:
            t.join()

    def _launch_without_adspower(self) -> None:
        for i in range(1, self.config.options.browsers_amount + 1):
            self._stagger_start(i)
            worker = BrowserWorker(index=i, config=self.config)
            t = threading.Thread(target=worker.run, daemon=True)
            self.threads.append(t)
            t.start()

    def _launch_with_adspower(self, adspower_ids: Sequence[str]) -> None:
        for i, adspower_id in enumerate(adspower_ids, start=1):
            self._stagger_start(i)
            worker = BrowserWorker(index=i, config=self.config, adspower_id=adspower_id)
            t = threading.Thread(target=worker.run, daemon=True)
            self.threads.append(t)
            t.start()

    @staticmethod
    def _stagger_start(worker_index: int) -> None:
        if worker_index != 1:
            time.sleep(worker_index * BETWEEN_WORKERS_STAGGER_SEC)


class EelApp:
    """Facade for Eel UI; translates UI inputs into AppConfig and runs the orchestrator."""

    def __init__(self, web_folder: str = "web") -> None:
        eel.init(web_folder)
        eel.expose(self.main)

    @staticmethod
    def _build_config(
        initial_url: str,
        is_nopecha: bool,
        browsers_amount: int,
        proxy_list: Sequence[str],
        is_madridista: bool,
        numero: Optional[str],
        contrasena: Optional[str],
        is_vpn: str,
        adspower_api: Optional[str],
        adspower_ids: Sequence[str] | str,
    ) -> AppConfig:
        creds = Credentials(numero=numero, contrasena=contrasena)
        opts = LaunchOptions(
            is_nopecha=is_nopecha,
            is_madridista=is_madridista,
            is_vpn=is_vpn,
            browsers_amount=int(browsers_amount),
            adspower_api=adspower_api,
            adspower_ids=normalize_adspower_ids(adspower_ids),
            proxy_list=proxy_list,
        )
        return AppConfig(initial_url=initial_url, credentials=creds, options=opts)

    
    def main(
        self,
        initial_url: str,
        is_nopecha: bool,
        browsers_amount: int,
        proxy_list: Sequence[str],
        is_madridista: bool,
        numero: Optional[str],
        contrasena: Optional[str],
        is_vpn: bool,
        adspower_api: Optional[str] = None,
        adspower_ids: Sequence[str] | str = (),
    ) -> None:
        "Launches workers based on user inputs from gui"
        
        log_line(
            "info",
            f"Launch requested: url={initial_url} nopecha={is_nopecha} "
            f"browsers={browsers_amount} madridista={is_madridista} vpn={is_vpn} "
            f"adspower_api={'set' if adspower_api else 'none'} ids={bool(adspower_ids)}",
        )

        config = self._build_config(
            initial_url=initial_url,
            is_nopecha=is_nopecha,
            browsers_amount=browsers_amount,
            proxy_list=proxy_list,
            is_madridista=is_madridista,
            numero=numero,
            contrasena=contrasena,
            is_vpn=is_vpn,
            adspower_api=adspower_api,
            adspower_ids=adspower_ids,
        )

        WorkersOrchestrator(config).launch()
    
    def start(self, starting_port: int = 8001, size: tuple[int, int] = (600, 900)) -> None:
        """Start the Eel app on the first available port"""
        port = starting_port
        while True:
            try:
                if not Ports.is_open("localhost", port):
                    eel.start("main.html", size=size, port=port)
                    return
                port+=1
            except OSError as e:
                logging.exception("Eel start error: %s", e)
        

def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


if __name__ == "__main__":
    _configure_logging()
    app = EelApp(web_folder="web")
    app.start()
