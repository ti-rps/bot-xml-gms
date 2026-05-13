import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class CancellationWatcher:
    """Background poller para o endpoint de cancelamento do maestro.

    Tem duas funções acopladas:
    1. Detectar quando o usuário pediu cancelamento via UI e sinalizar o bot.
    2. Servir de heartbeat — cada GET atualiza last_heartbeat_at no maestro,
       impedindo que o retry worker considere o job órfão (janela de 5min).

    Uso recomendado como context manager:

        with CancellationWatcher(check_fn, job_id, on_cancel=...) as watcher:
            run_bot(cancel_event=watcher.cancel_event)
    """

    def __init__(
        self,
        check_fn: Callable[[str], bool],
        job_id: str,
        poll_interval: float = 15.0,
        on_cancel: Optional[Callable[[], None]] = None,
    ):
        self.check_fn = check_fn
        self.job_id = job_id
        self.poll_interval = poll_interval
        self.on_cancel = on_cancel
        self.cancel_event = threading.Event()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def _run(self) -> None:
        logger.info(
            f"🔭 CancellationWatcher iniciado (job {self.job_id}, intervalo {self.poll_interval}s)"
        )
        while not self._stop_event.is_set():
            try:
                if self.check_fn(self.job_id):
                    logger.warning(f"🛑 Cancelamento solicitado para job {self.job_id}")
                    if self.on_cancel is not None:
                        try:
                            self.on_cancel()
                        except Exception as cb_err:
                            logger.warning(
                                f"CancellationWatcher: callback on_cancel falhou: {cb_err}"
                            )
                    self.cancel_event.set()
                    return
            except Exception as poll_err:
                # WHY warning, não error: blip de rede ou restart do maestro não
                # deve abortar o job. Tenta de novo no próximo ciclo.
                logger.warning(
                    f"CancellationWatcher: falha transiente no poll: {poll_err}"
                )

            # _stop_event.wait permite encerrar rápido quando stop() é chamado.
            self._stop_event.wait(timeout=self.poll_interval)

        logger.info(f"🔭 CancellationWatcher encerrado (job {self.job_id})")

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run,
            name=f"cancel-watcher-{self.job_id}",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def __enter__(self) -> "CancellationWatcher":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.stop()
        return False
