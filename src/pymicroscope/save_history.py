from mytk import Window, TableView, App
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from typing import Optional
import mimetypes
from pymicroscope.utils.thread_utils import is_main_thread

@dataclass
class FileInfo:
    path: Path
    size_bytes: int
    created_time: Optional[datetime] = None
    mime_type:Optional[str] = None
        
    @classmethod
    def from_path(cls, path: Path) -> 'FileInfo':
        stat = path.stat()
        mime_type, _ = mimetypes.guess_type(str(path))
        return cls(
            path=path,
            size_bytes=stat.st_size,
            created_time=datetime.fromtimestamp(stat.st_ctime),
            mime_type = mime_type,
        )
    
    def as_dict(self):
        return {'path':str(self.path), 'filename':str(self.path.name), 'size_bytes':self.size_bytes, 'created_time':self.created_time}
            
class SaveHistory:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.files = []
        self.window = Window(title="Save history", geometry="300x600+1200+0")
        self.window.widget.rowconfigure(0, weight=1)
        self.window.widget.columnconfigure(0, weight=1)

        self.tableview:TableView = TableView(columns_labels={"filepath":"Filepath", 'filename':'Name', 'size_bytes':'Size', 'created_time':'Date created'})
        self.tableview.grid_into(self.window, padx=10, pady=10, sticky='nsew')
        self.tableview.column_formats = {"filepath":{'type':str,'anchor':'w'}}
        self.tableview.displaycolumns = ['filename']        
        self.tableview.all_elements_are_editable = False
        self.tableview.delegate = self
        
    def add(self, filepath:Path):
        assert is_main_thread()
        
        file_info = FileInfo.from_path(filepath)
        self.files.append(file_info.as_dict())
        
        record = file_info.as_dict()
        self.tableview.data_source.append_record(record)
        
    def doubleclick_cell(self, item_id:str, column_name:str, tableview:TableView):
        record = tableview.data_source.record(item_id)
        App.app.reveal_path(record['path'])
    