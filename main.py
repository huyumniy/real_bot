import time
import asyncio
import threading
from typing import List, Optional, Sequence

from utils.helpers import log_line, clean_adspower_ids, \
    build_adspower_profile_url, generate_profile_name
from utils.driver_controller import DriverController
from config import AppConfig
from eel_app import EelApp

BETWEEN_WORKERS_STAGGER_SEC = 15.0

class MainLoop:
    """
    Periodically inspects and maintains browser tab state via `DriverController`.

    This class runs continuously in an asyncio loop, invoking the controller's checks
    and recovery routines on all open browser tabs at fixed intervals.

    Responsibilities:
    - Keep the browser session active by calling DriverController methods.
    - Handle exceptions gracefully to ensure continuous operation.
    
    note:
    MainLoop does not implement the maintenance logic itself; it relies on DriverController for that.
    """
    def __init__(self, controller: DriverController) -> None:
        self.controller = controller
        self._running = False

    async def run(self) -> None:
        self._running = True
        while self._running:
            try:
                
                for t in list(self.controller.driver.tabs):
                    await self.controller.recover_if_blocked(t)
                    await self.controller.reload_initial_if_home_redirect(t)
                    await self.controller.click_verify(self.controller.driver, t)
                    
                    if 'oneboxtm.queue-it.net/error' in t.url \
                     or 'oneboxtm.queue-it.net/error403' in t.url:
                        await self.controller.change_proxy(t)
                        await t.get(self.controller.initial_url)
                    await self.controller.check_for_element(t,\
                    '#buttonConfirmRedirect', click=True)
                
                await asyncio.sleep(5)

            except Exception as exc:
                log_line("error", f"MainLoop error: {exc}")
                await asyncio.sleep(5.0)

    def stop(self) -> None:
        self._running = False


class BrowserWorker:
    """
    An autonomous browser worker running in its own thread.

    Lifecycle:
    - `run()` creates a new asyncio event loop bound to the thread and runs `_run_async()`.
    - `_run_async()` initializes the DriverController, performs setup/navigation, then
      starts the `MainLoop` to maintain browser state.
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
        link = build_adspower_profile_url(self.config.options.adspower_api, self.adspower_id)
        profile = generate_profile_name(self.index, self.adspower_id)

        self.controller = DriverController(
            initial_url=self.config.initial_url,
            proxy_list=self.config.options.proxy_list,
            profile_name=profile,
            adspower_link=link,
        )

        await self.controller.setup_driver()
        await self.controller.post_connect_setup()
        await self.controller.navigate_to_initial_url()

        loop = MainLoop(self.controller)
        await loop.run()


class WorkersOrchestrator:
    """
    Creates and manages browser workers; public entry is `launch()`.

    Behavior:
    - If Adspower IDs and API are provided, launches one worker per profile.
    - Otherwise launches a fixed number of plain browser workers `browser_amount`.
    - Starts workers with a stagger to avoid bursty resource use.
    - Blocks the caller via `join()` until all worker threads exit.

    note:
    staggering can be disabled by setting `is_stagger_enabled` to False.
    """
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.threads: List[threading.Thread] = []
        self.is_stagger_enabled = True

    def launch(self) -> None:
        """Launch workers either with AdsPower profiles or plain multi-browser run."""
        opts = self.config.options
        adspower_ids = clean_adspower_ids(opts.adspower_ids)

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

    def _stagger_start(self, worker_index: int) -> None:
        if worker_index != 1 and self.is_stagger_enabled:
            time.sleep(worker_index * BETWEEN_WORKERS_STAGGER_SEC)

def _launch(config):
    WorkersOrchestrator(config).launch()

if __name__ == "__main__":
    app = EelApp(web_folder="web", on_launch=_launch)
    app.start()
