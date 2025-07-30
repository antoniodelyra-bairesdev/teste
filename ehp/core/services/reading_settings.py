from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from ehp.core.models.schema.reading_settings import (
    ColorMode,
    FontOption,
    FontSize,
    FontWeight,
    LineSpacing,
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


def _create_validation_error_response(validation_error: ValidationError) -> HTTPException:
    """
    Create user-friendly error messages from Pydantic ValidationError.

    Args:
        validation_error: The ValidationError from Pydantic

    Returns:
        HTTPException with status 422 and detailed error messages
    """
    friendly_errors = []

    for error in validation_error.errors():
        field_path = ".".join(str(loc) for loc in error.get("loc", []))
        error_type = error.get("type", "")

        # Create field-specific error messages
        if "font_size" in field_path:
            valid_options = [e.value for e in FontSize]
            friendly_errors.append(
                f"Font size must be one of: {', '.join(valid_options)}"
            )
        elif "font_weight" in field_path:
            valid_options = [e.value for e in FontWeight]
            friendly_errors.append(
                f"Font weight must be one of: {', '.join(valid_options)}"
            )
        elif "line_spacing" in field_path:
            valid_options = [e.value for e in LineSpacing]
            friendly_errors.append(
                f"Line spacing must be one of: {', '.join(valid_options)}"
            )
        elif "color_mode" in field_path:
            valid_options = [e.value for e in ColorMode]
            friendly_errors.append(
                f"Color mode must be one of: {', '.join(valid_options)}"
            )
        elif "fonts" in field_path:
            if "headline" in field_path or "body" in field_path or "caption" in field_path:
                valid_fonts = [e.value for e in FontOption]
                friendly_errors.append(
                    f"Font must be one of: {', '.join(valid_fonts)}"
                )
            elif "required" in error_type:
                friendly_errors.append("Font settings are required")
            else:
                friendly_errors.append(
                    f"Invalid font setting: {error.get('msg', 'Unknown error')}"
                )
        else:
            # Fallback for unknown fields
            friendly_errors.append(
                f"Invalid value for {field_path}: {error.get('msg', 'Unknown error')}"
            )

    # If no specific errors were mapped, use generic message
    if not friendly_errors:
        friendly_errors.append("Invalid reading settings format")

    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "message": "Reading settings validation failed",
            "errors": friendly_errors
        }
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

    - **font_size**: Text size preference (Small, Medium, Large)
    - **fonts**: Font family preferences for different text types
        - **headline**: Font for headlines and titles
        - **body**: Font for main content text
        - **caption**: Font for captions and small text
    - **font_weight**: Font weight preference (Light, Normal, Bold)
    - **line_spacing**: Line spacing preference (Compact, Standard, Spacious)
    - **color_mode**: Color mode preference including accessibility options

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
    except ValidationError as e:
        raise _create_validation_error_response(e)
    except Exception:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
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
        - **font_size**: Text size preference (Small, Medium, Large)
        - **fonts**: Font family preferences for different text types
        - **font_weight**: Font weight preference (Light, Normal, Bold)
        - **line_spacing**: Line spacing preference (Compact, Standard, Spacious)
        - **color_mode**: Color mode preference including accessibility options

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
        "line_spacing": "Spacious",
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
        "line_spacing": "Spacious",
        "color_mode": "Dark"
    }
    ```

    **Error Response (Invalid font size):**
    ```json
    {
        "detail": {
            "message": "Reading settings validation failed",
            "errors": [
                "Font size must be one of: Small, Medium, Large"
            ]
        }
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
    except ValidationError as e:
        raise _create_validation_error_response(e)
    except Exception:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
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
        - **color_mode**: Color mode preference (optional)

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
        "font_size": "Large",
        "color_mode": "Dark"
    }
    ```

    **Response (Complete settings after merge):**
    ```json
    {
        "font_size": "Large",
        "fonts": {
            "headline": "Arial",
            "body": "Georgia",
            "caption": "Verdana"
        },
        "font_weight": "Bold",
        "line_spacing": "Spacious",
        "color_mode": "Dark"
    }
    ```

    **Error Response (Invalid color mode):**
    ```json
    {
        "detail": {
            "message": "Reading settings validation failed",
            "errors": [
                "Color mode must be one of: Default, Dark, Red-Green Color Blindness, "
                "Blue-Yellow Color Blindness"
            ]
        }
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

        # Validate merged settings by creating a ReadingSettings instance
        validated_settings = ReadingSettings(**new_settings)

        # Save merged settings
        await repository.update_reading_settings(
            user.user.id, validated_settings.model_dump()
        )

        return validated_settings
    except UserNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except ValidationError as e:
        raise _create_validation_error_response(e)
    except Exception:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
