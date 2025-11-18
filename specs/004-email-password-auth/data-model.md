# Data Model: Email & Password Authentication

This document describes the necessary changes to the data model to support email and password authentication. The primary change is to the `User` entity.

## User Entity

**File Location**: `backend/src/models/user.py`

The `User` model needs to be updated to store a password hash for users who register via email.

### New Fields

| Field Name | Data Type | Description | Constraints |
| :--- | :--- | :--- | :--- |
| `hashed_password` | `String` | The salted and hashed password for the user. | `nullable=True` |

### Rationale for Nullable

The `hashed_password` field must be nullable (`nullable=True`) to accommodate existing and future users who authenticate via third-party providers like Google OAuth. These users will not have a password stored in our system, so their `hashed_password` field will be `NULL`.

### Example SQLAlchemy Model Update

```python
# In backend/src/models/user.py

from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    
    # Existing fields for Google auth
    google_id = Column(String, unique=True, index=True, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # New field for email/password auth
    hashed_password = Column(String, nullable=True)

    # Other fields remain unchanged
    # ...
```
