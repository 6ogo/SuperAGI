from __future__ import annotations

from sqlalchemy import Column, Integer, String
import requests

# from superagi.models import AgentConfiguration
from superagi.models.base_model import DBBaseModel

#marketplace_url = "https://app.superagi.com/api"
marketplace_url = "http://localhost:8001"

class Knowledges(DBBaseModel):
    """
    Represents an knowledge entity.

    Attributes:
        id (int): The unique identifier of the knowledge.
        name (str): The name of the knowledge.
        description (str): The description of the knowledge.
        summary (str): The summary of the knowledge description.
        readme (str): The readme associated with the embedding.
        index_id (int): The index associated with the knowledge.
        is_deleted (int): The flag for deletion/uninstallation of a knowledge.
        organisation_id (int): The identifier of the associated organisation.
    """

    __tablename__ = 'knowledges'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    description = Column(String)
    summary = Column(String)
    readme = Column(String)
    vector_db_index_id = Column(Integer)
    organisation_id = Column(Integer)
    contributed_by = Column(String)

    def __repr__(self):
        """
        Returns a string representation of the Knowledge object.

        Returns:
            str: String representation of the Knowledge.

        """
        return f"Knowledge(id={self.id}, name='{self.name}', description='{self.description}', " \
               f"summary='{self.summary}', readme='{self.readme}', index_id={self.index_id}), " \
               f"organisation_id={self.organisation_id}), contributed_by={self.contributed_by}"