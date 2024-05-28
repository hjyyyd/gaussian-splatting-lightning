import time

from lightning.pytorch.callbacks import Callback


class SaveGaussian(Callback):
    def on_train_end(self, trainer, pl_module) -> None:
        # TODO: should save before densification
        pl_module.save_gaussians()


class KeepRunningIfWebViewerEnabled(Callback):
    def on_train_end(self, trainer, pl_module) -> None:
        if pl_module.web_viewer is None:
            return
        print("Training finished! Web viewer is still running. Press `Ctrl+C` to exist.")
        while True:
            pl_module.web_viewer.is_training_paused = True
            pl_module.web_viewer.process_all_render_requests(pl_module.gaussian_model, pl_module.renderer, pl_module._fixed_background_color())


class StopImageSavingThreads(Callback):
    def on_exception(self, trainer, pl_module, exception: BaseException) -> None:
        alive_threads = pl_module.image_saving_threads

        while len(alive_threads) > 0:
            # send messages to terminate threads
            while True:
                try:
                    pl_module.image_queue.put(None, block=False)
                except:
                    break

            # check whether any threads are alive
            still_alive_threads = []
            for thread in alive_threads:
                if thread.is_alive() is True:
                    still_alive_threads.append(thread)
            alive_threads = still_alive_threads
