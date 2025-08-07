from mytk import Window, TableView, TabularData, App
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
            
class SaveHistory:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.files = []
        self.window = Window(title="Save history", geometry="300x400")
        self.window.widget.rowconfigure(0, weight=1)
        self.window.widget.columnconfigure(0, weight=1)

        self.tableview = TableView(columns_labels={"filepath":"Filepath"})
        self.tableview.grid_into(self.window, padx=10, pady=10, sticky='nsew')
        self.tableview.column_formats = {"filepath":{'type':str,'anchor':'w'}}
        
        
    def add(self, filepath):
        assert is_main_thread()
        
        file_info = FileInfo.from_path(filepath)
        self.files.append(file_info)
        
        record = {"filepath":str(filepath)}

        self.tableview.data_source.append_record(record)
        self.tableview.source_data_added_or_updated([record])
        
        
    