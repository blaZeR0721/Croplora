from croploraApp.models import Address
from rest_framework import serializers
from croploraApp.models import State,Country

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "address_line_1",
            "address_line_2",
            "country",
            "state",
            "postal_code",
            "landmark",
        ]
        extra_kwargs = {
            "address_line_1": {
                "required": True,
                "allow_blank": False,
                "trim_whitespace": True,
            },
        }

    def validate(self, attrs):
        country = attrs.get("country")
        state = attrs.get("state")

        if state and not country:
            raise serializers.ValidationError(
                {"country": "Country is required when state is provided."}
            )

        # Ensure the state belongs to the selected country.
        if country and state and state.country_id != country.id:
            raise serializers.ValidationError(
                {"state": "The selected state does not belong to the selected country."}
            )

        return attrs


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["id", "name", "iso2"]

class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ["id", "name", "country"]