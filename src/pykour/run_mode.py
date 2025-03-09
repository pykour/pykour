import os


class RunMode:
    ENVIRONMENTS = {
        "prod": ("production", "prod", "prd"),
        "dev": ("development", "dev"),
    }
    PRODUCTION = "prod"
    DEVELOPMENT = "dev"

    @classmethod
    def is_production(cls) -> bool:
        return cls._get_env() == cls.PRODUCTION

    @classmethod
    def is_development(cls) -> bool:
        return cls._get_env() == cls.DEVELOPMENT

    @classmethod
    def _get_env(cls) -> str:
        _current_mode = cls.DEVELOPMENT

        env = cls._match_env(os.getenv("PYKOUR_ENV", cls.DEVELOPMENT))

        if env == cls.PRODUCTION:
            _current_mode = cls.PRODUCTION
        elif env == cls.DEVELOPMENT:
            _current_mode = cls.DEVELOPMENT

        return _current_mode

    @classmethod
    def _match_env(cls, env_name: str) -> bool:
        for key, values in cls.ENVIRONMENTS.items():
            if env_name in values:
                return key
        return cls.DEVELOPMENT
