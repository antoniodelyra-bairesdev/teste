from fastapi import APIRouter, Depends, HTTPException, status

from ehp.core.models.schema.reading_settings import (
    ReadingSettings,
    ReadingSettingsUpdate,
)
from ehp.core.repositories.user import UserNotFoundException, UserRepository
from ehp.core.services.session import AuthContext
from ehp.db.db_manager import ManagedAsyncSession
from ehp.utils.authentication import needs_api_key

router = APIRouter(
    prefix="/users",
    tags=["Reading Settings"],
    dependencies=[Depends(needs_api_key)],
    responses={404: {"description": "Not found"}},
)


@router.get("/reading-settings")
async def get_reading_settings(
    user: AuthContext,
    db_session: ManagedAsyncSession,
) -> ReadingSettings:
    """
    Get user's reading settings.

    This endpoint retrieves the current reading settings for the authenticated user.
    If the user has no custom settings configured, it returns a set of default values
    that provide a good reading experience.

    ## Returns

    `ReadingSettings` containing:

    - **font_size**: Text size preference (Small, Medium, Large, Extra Large)
    - **fonts**: Font family preferences for different text types
        - **headline**: Font for headlines and titles
        - **body**: Font for main content text
        - **caption**: Font for captions and small text
    - **font_weight**: Font weight preference (Light, Normal, Bold)
    - **line_spacing**: Line spacing preference (Compact, Standard, Wide)
    - **color_mode**: Color theme preference (Default, Light, Dark)

    ## Raises

    - `HTTPException`: 404 if user is not found
    - `HTTPException`: 500 if an internal server error occurs

    ## Example

    **Request:**
    ```
    GET /users/reading-settings
    ```

    **Response:**
    ```json
    {
        "font_size": "Medium",
        "fonts": {
            "headline": "System",
            "body": "System",
            "caption": "System"
        },
        "font_weight": "Normal",
        "line_spacing": "Standard",
        "color_mode": "Default"
    }
    ```

    **Error Response (User not found):**
    ```json
    {
        "detail": "User not found"
    }
    ```
    """
    try:
        repository = UserRepository(db_session)
        settings_dict = await repository.get_reading_settings(user.user.id)
        return ReadingSettings(**settings_dict)
    except UserNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@router.post("/reading-settings", status_code=status.HTTP_201_CREATED)
async def create_reading_settings(
    settings: ReadingSettings,
    user: AuthContext,
    db_session: ManagedAsyncSession,
) -> ReadingSettings:
    """
    Create or overwrite user's reading settings.

    This endpoint allows users to set their complete reading preferences by providing
    all settings at once. If the user already has settings configured, they will be
    completely replaced with the new values.

    ## Parameters

    - **settings**: Complete reading settings configuration
        - **font_size**: Text size preference (Small, Medium, Large, Extra Large)
        - **fonts**: Font family preferences for different text types
        - **font_weight**: Font weight preference (Light, Normal, Bold)
        - **line_spacing**: Line spacing preference (Compact, Standard, Wide)
        - **color_mode**: Color theme preference (Default, Light, Dark)

    ## Returns

    `ReadingSettings` containing the saved configuration

    ## Raises

    - `HTTPException`: 404 if user is not found
    - `HTTPException`: 422 if validation fails (invalid settings format)
    - `HTTPException`: 500 if an internal server error occurs

    ## Example

    **Request:**
    ```
    POST /users/reading-settings

    {
        "font_size": "Large",
        "fonts": {
            "headline": "Arial",
            "body": "Georgia",
            "caption": "Verdana"
        },
        "font_weight": "Bold",
        "line_spacing": "Wide",
        "color_mode": "Dark"
    }
    ```

    **Response:**
    ```json
    {
        "font_size": "Large",
        "fonts": {
            "headline": "Arial",
            "body": "Georgia",
            "caption": "Verdana"
        },
        "font_weight": "Bold",
        "line_spacing": "Wide",
        "color_mode": "Dark"
    }
    ```

    **Error Response (Invalid settings):**
    ```json
    {
        "detail": [
            {
                "loc": ["body", "font_size"],
                "msg": "value is not a valid enumeration member",
                "type": "type_error.enum"
            }
        ]
    }
    ```
    """
    try:
        repository = UserRepository(db_session)
        await repository.update_reading_settings(user.user.id, settings.model_dump())
        return settings
    except UserNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


@router.put("/reading-settings")
async def update_reading_settings(
    settings_update: ReadingSettingsUpdate,
    user: AuthContext,
    db_session: ManagedAsyncSession,
) -> ReadingSettings:
    """
    Update user's reading settings (merge with existing).

    This endpoint allows users to partially update their reading settings by providing
    only the fields they want to change. The provided settings will be merged with
    the existing configuration, preserving any settings not included in the update.

    ## Parameters

    - **settings_update**: Partial reading settings update (only include fields to change)
        - **font_size**: Text size preference (optional)
        - **fonts**: Font family preferences (optional, can be partial)
        - **font_weight**: Font weight preference (optional)
        - **line_spacing**: Line spacing preference (optional)
        - **color_mode**: Color theme preference (optional)

    ## Returns

    `ReadingSettings` containing the complete updated configuration

    ## Raises

    - `HTTPException`: 404 if user is not found
    - `HTTPException`: 422 if validation fails (invalid settings format)
    - `HTTPException`: 500 if an internal server error occurs

    ## Example

    **Request (Update only font size and color mode):**
    ```
    PUT /users/reading-settings

    {
        "font_size": "Extra Large",
        "color_mode": "Light"
    }
    ```

    **Response (Complete settings after merge):**
    ```json
    {
        "font_size": "Extra Large",
        "fonts": {
            "headline": "Arial",
            "body": "Georgia",
            "caption": "Verdana"
        },
        "font_weight": "Bold",
        "line_spacing": "Wide",
        "color_mode": "Light"
    }
    ```

    **Request (Update only specific fonts):**
    ```
    PUT /users/reading-settings

    {
        "fonts": {
            "headline": "Times New Roman",
            "body": "Helvetica"
        }
    }
    ```

    **Response (Fonts merged with existing):**
    ```json
    {
        "font_size": "Large",
        "fonts": {
            "headline": "Times New Roman",
            "body": "Helvetica",
            "caption": "Verdana"
        },
        "font_weight": "Bold",
        "line_spacing": "Wide",
        "color_mode": "Dark"
    }
    ```

    **Error Response (User not found):**
    ```json
    {
        "detail": "User not found"
    }
    ```
    """
    try:
        repository = UserRepository(db_session)

        # Get current settings
        current_settings = await repository.get_reading_settings(user.user.id)
        new_settings = current_settings.copy()

        # Merge update with current settings
        updated_data = settings_update.model_dump(exclude_unset=True)
        new_settings.update(updated_data)

        # Save merged settings
        await repository.update_reading_settings(user.user.id, new_settings)

        return ReadingSettings(**new_settings)
    except UserNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )
