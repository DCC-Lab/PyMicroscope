
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
from typing import Optional
import mimetypes

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
    
    def add(self, filepath):
        file_info = FileInfo.from_path(filepath)
        self.files.append(file_info)
        print(self.files)
        
    