from beanie import PydanticObjectId

from app.core.models import Project as ProjectModel
from app.core.types import Project as ProjectType


class ProjectRepository:
    @staticmethod
    async def get_by_id(project_id: str) -> ProjectType | None:
        try:
            project = await ProjectModel.get(PydanticObjectId(project_id))
            return ProjectType.from_model(project) if project else None
        except Exception:
            return None

    @staticmethod
    async def get_all() -> list[ProjectType]:
        projects = await ProjectModel.find_all().to_list()
        return [ProjectType.from_model(project) for project in projects]

    @staticmethod
    async def add_or_get_existing(project_data: ProjectType) -> ProjectType:
        existing_project = await ProjectModel.find_one(ProjectModel.name == project_data.name)

        if existing_project:
            return ProjectType.from_model(existing_project)

        new_project_model = project_data.to_model()
        await new_project_model.save()

        return ProjectType.from_model(new_project_model)

    @staticmethod
    async def is_existing(name: str) -> bool:
        existing_project = await ProjectModel.find_one(ProjectModel.name == name)
        return existing_project is not None
