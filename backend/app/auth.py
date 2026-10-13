from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from .config import settings

_bearer = HTTPBearer(auto_error=False)
_jwks_client = PyJWKClient(settings.keycloak_jwks_url, cache_keys=True, lifespan=600)


@dataclass(frozen=True)
class Principal:
    sub: str
    username: str
    roles: frozenset[str]

    def has_role(self, role: str) -> bool:
        return role in self.roles


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def decode_token(token: str) -> dict:
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.keycloak_audience,
            issuer=settings.keycloak_issuer,
            options={"require": ["exp", "iat", "sub", "iss"]},
        )
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Token expired")
    except jwt.InvalidAudienceError:
        raise _unauthorized("Token is not intended for reports-api")
    except jwt.InvalidIssuerError:
        raise _unauthorized("Token issued by unknown issuer")
    except jwt.PyJWTError as exc:
        raise _unauthorized(f"Invalid token: {exc}")


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("Missing bearer token")

    claims = decode_token(credentials.credentials)
    username = claims.get("preferred_username")
    if not username:
        raise _unauthorized("Token has no preferred_username claim")

    roles = frozenset(claims.get("realm_access", {}).get("roles", []))
    return Principal(sub=claims["sub"], username=username, roles=roles)


async def require_prosthesis_user(
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    if not principal.has_role(settings.required_role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{settings.required_role}' is required to access reports",
        )
    return principal
