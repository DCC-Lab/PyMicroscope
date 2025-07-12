import time
from queue import Queue, Empty, Full
from multiprocessing import Queue
from contextlib import suppress
from pathlib import Path
import numpy as np
from datetime import datetime

from PIL import Image as PILImage

from pymicroscope.utils.terminable import run_loop, TerminableProcess
from threading import Thread

class SaveTask(TerminableProcess):
    def __init__(self, n_images, root_dir=None, template=None, save_individual_files=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.n_images = n_images
        self.root_dir = root_dir
        self.save_individual_files = save_individual_files
        if self.root_dir is None:
            self.root_dir = Path("/tmp").expanduser()
        
        self.template = template
        if template is None:
            self.template = "Image-{date}-{time}-{i:03d}.tif"
            
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
                        
                        now = datetime.now()

                        date_str = now.strftime("%Y%m%d")
                        time_str = now.strftime("%H%M%S")
                        params = {"date":date_str, "time":time_str}

                        while index < self.n_images:
                            img_array = self.queue.get()
                            img_arrays.append(img_array)
                            
                            if self.save_individual_files:
                                pil_image = PILImage.fromarray(img_array, mode="RGB")                            
                                params["i"]= index
                                filepath = self.root_dir / Path(self.template.format(**params))
                                pil_image.save(filepath)
                                print(f"Saving {filepath}")                                
                            index = index+1
                            
                        print(f"{index} images saved")
                        stacked = np.stack(img_arrays).astype(np.float64)
                        mean_img = np.mean(stacked, axis=0)
                        pil_image = PILImage.fromarray(mean_img.astype(np.uint8), mode="RGB")
                        params['i'] = "avg"                     
                        filepath = self.root_dir / Path(self.template.format(**params))
                        pil_image.save(filepath)
                        
                        must_terminate_now = True
                    else:
                        time.sleep(0.01)
                        
                except Exception as err:
                    self.log.error(f"Error in ImageProvider run loop : {err}")

            self.empty_queue(self.queue)
            self.queue.close()
            self.queue.join_thread()                           
        