from django.contrib.auth.hashers import BasePasswordHasher
from passlib.hash import phpass as phpass_hasher


class PhpassPasswordHasher(BasePasswordHasher):
    """Verify migrated WordPress phpass hashes; auto-upgrades to Argon2 on login."""
    algorithm = 'phpass'

    def encode(self, password, salt):
        hash_val = phpass_hasher.hash(password)[3:]  # strip '$P$'
        return f'phpass$${hash_val}'

    def verify(self, password, encoded):
        _, _, hashed = encoded.split('$', 2)
        try:
            return phpass_hasher.verify(password, '$P$' + hashed)
        except Exception:
            return False

    def safe_summary(self, encoded):
        return {'algorithm': self.algorithm}

    def must_update(self, encoded):
        return True  # always upgrade to Argon2 on next login
