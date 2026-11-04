from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        # alias_generator : 필드마다 camelCase 별칭을 자동으로 만든다. (menu_name -> menuName)
        alias_generator=to_camel,
        # populate_by_name : 별칭(menuName)뿐 아니라 파이썬 이름(menu_name)으로도 값을 넣을 수 있게 한다.
        populate_by_name=True,
    )
