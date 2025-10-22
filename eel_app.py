from config import AppConfig, Credentials, LaunchOptions
from typing import Callable, Optional, Sequence
from utils.helpers import log_line, clean_adspower_ids, is_port_open
import eel

class EelApp:
    """
    Facade class that connects Eel frontend GUI with the python backend.
    
    This class is responsible for:
    - Drawing GUI on the screen.
    - Exposing listener that receives parameters from the GUI.
    - Converting those parameters into an AppConfig, and passing them to the WorkersOrchestrator.
    - Automatically finding an available port to run the Eel app on.

    note:
    - eel.expose(self.main) makes the main method callable from javascript.
    - "web/main.html" is the main GUI file.
    - GUI size is set to 600x900 pixels.
    
    note:
    - The GUI runs on localhost. If you are running this on a remote server, ensure that
    localhost access is not blocked by a firewall, proxy, or VPN.
    You may need to adjust your firewall rules or disable any networks filters that interfere
    with local connections for the GUI to start properly.
    """

    def __init__(self, web_folder: str = "web", on_launch: Callable[[AppConfig], None] | None = None) -> None:
        eel.init(web_folder)
        eel.expose(self.main)
        self.on_launch = on_launch

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
            browsers_amount=int(browsers_amount) if browsers_amount else None,
            adspower_api=adspower_api,
            adspower_ids=clean_adspower_ids(adspower_ids),
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
        """Main entry point exposed to the Eel GUI."""
        
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

        if self.on_launch:
            self.on_launch(config)
        else:
            log_line("warning", "No on_launch handler set; launch aborted.")
    
    def start(
        self,
        starting_port: int = 8001,
        size: tuple[int, int] = (600, 900)
    ) -> None:
        """Start the Eel app on the first available port."""
        port = starting_port
        while True:
            try:
                if not is_port_open("localhost", port):
                    eel.start("main.html", size=size, port=port)
                    return
                port+=1
            except OSError as e:
                log_line("error", f"Eel start error: {e}")
        