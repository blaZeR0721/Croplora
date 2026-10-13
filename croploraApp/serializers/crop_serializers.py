from rest_framework import serializers

from croploraApp.models.agriculture import Crop


class CropCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crop
        fields = [
            "id",
            "crop_code",
            "name",
            "crop_type",
            "variety",
            "scientific_name",
            "description",
        ]
        read_only_fields = ["id", "crop_code"]
        extra_kwargs = {
            "name": {
                "required": True,
                "allow_blank": False,
                "trim_whitespace": True,
            },
            "crop_type": {"required": True},
            "variety": {
                "required": False,
                "allow_blank": True,
                "trim_whitespace": True,
            },
            "scientific_name": {
                "required": False,
                "allow_null": True,
                "allow_blank": True,
                "trim_whitespace": True,
            },
            "description": {
                "required": False,
                "allow_null": True,
                "allow_blank": True,
            },
        }

    def validate(self, attrs):
        request = self.context.get("request")
        organization_id = getattr(getattr(request, "user", None), "organization_id", None)
        if organization_id is None:
            raise serializers.ValidationError(
                {"organization": "Your user must belong to an organization."}
            )

        name = attrs.get("name", self.instance.name if self.instance else "")
        variety = attrs.get(
            "variety",
            self.instance.variety if self.instance else "",
        )
        name = name.strip()
        variety = variety.strip()

        if self.instance and (
            name.casefold() == self.instance.name.casefold()
            and variety.casefold() == self.instance.variety.casefold()
        ):
            return attrs

        duplicate_crops = Crop.objects.filter(
            organization_id=organization_id,
            name__iexact=name,
            variety__iexact=variety,
        )
        if self.instance:
            duplicate_crops = duplicate_crops.exclude(pk=self.instance.pk)

        if duplicate_crops.exists():
            raise serializers.ValidationError(
                {"name": "A crop with this name and variety already exists."}
            )

        return attrs


class CropListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crop
        fields = ["id", "crop_code", "name", "crop_type", "variety"]
        read_only_fields = fields