from queue import Queue, Empty, Full
from multiprocessing import Queue
from contextlib import suppress
from pathlib import Path
import numpy as np

from PIL import Image as PILImage

from pymicroscope.utils.terminable import run_loop, TerminableProcess


class SaveTask(TerminableProcess):
    def __init__(self, n_images, root_dir=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.n_images = n_images
        self.root_dir = root_dir
        if self.root_dir is None:
            self.root_dir = Path("/tmp").expanduser()
            
        self.queue = Queue(maxsize=n_images)
    
    def empty_queue(self, queue):
        try:
            while queue.get(timeout=0.1) is not None:
                pass
        except Empty:
            pass

    def run(self):
        with self.syncing_context() as must_terminate_now:
            while not must_terminate_now:
                try:
                    if self.queue.full():
                        print("Queue is ready for saving")       

                        index = 0
                        img_arrays = []
                        while index < self.n_images:
                            img_array = self.queue.get()
                            img_arrays.append(img_array)
                            
                            pil_image = PILImage.fromarray(img_array, mode="RGB")                            
                            filepath = self.root_dir / Path(f'test-{index:03d}.tiff')
                            pil_image.save(filepath)
                            print(f"Saving {filepath}")                                
                            index = index+1
                            
                        print(f"{index} images saved")
                        stacked = np.stack(img_arrays).astype(np.float64)
                        mean_img = np.mean(stacked, axis=0)
                        pil_image = PILImage.fromarray(mean_img.astype(np.uint8), mode="RGB")                            
                        filepath = self.root_dir / Path(f'test-avg.tiff')
                        pil_image.save(filepath)
                        
                        must_terminate_now = True
                except Exception as err:
                    self.log.error(f"Error in ImageProvider run loop : {err}")

            self.empty_queue(self.queue)
            self.queue.close()
            self.queue.join_thread()                           
        