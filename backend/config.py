from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    neo4j_uri: str
    neo4j_username: str
    neo4j_password: str
    neo4j_query_url: str | None = None  # HTTP Query API: https://xxxx.databases.neo4j.io/db/xxxx/query/v2

    pinecone_api_key: str
    pinecone_index_name: str = "ycmind"

    openai_api_key: str

    langsmith_api_key: str | None = None
    langsmith_project: str = "ycmind"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
