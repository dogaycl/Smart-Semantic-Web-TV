from app.models.user_profile import UserProfile


class UserProfileRepository:
    def create(
        self,
        *,
        user_id: int,
        display_name: str,
        avatar_url: str | None,
        interests: list[str],
        preferred_categories: list[str],
    ) -> UserProfile:
        return UserProfile(
            user_id=user_id,
            display_name=display_name,
            avatar_url=avatar_url,
            interests=interests,
            preferred_categories=preferred_categories,
        )

    def update(
        self,
        *,
        profile: UserProfile,
        display_name: str | None,
        avatar_url: str | None,
        interests: list[str] | None,
        preferred_categories: list[str] | None,
    ) -> UserProfile:
        if display_name is not None:
            profile.display_name = display_name
        if avatar_url is not None:
            profile.avatar_url = avatar_url
        if interests is not None:
            profile.interests = interests
        if preferred_categories is not None:
            profile.preferred_categories = preferred_categories
        return profile
