from pydantic import BaseModel
from typing import List, Optional

class Promptschema(BaseModel):
    system : str
    user : str
    context : Optional[str] = None

    def format(self) -> List:
        messages = [
            {"role": "system", "content": self.system.format(context=self.context) if self.context else self.system},
            {"role": "user", "content": self.user}
            ]
        return messages