import decimal
from unittest import TestCase

import pydantic
from piccolo.columns import Integer, Numeric, Varchar
from piccolo.columns.column_types import JSON, JSONB, Secret
from piccolo.table import Table
from pydantic import ValidationError

from piccolo_api.crud.serializers import create_pydantic_model


class TestVarcharColumn(TestCase):
    def test_varchar_length(self):
        class Director(Table):
            name = Varchar(length=10)

        pydantic_model = create_pydantic_model(table=Director)

        with self.assertRaises(ValidationError):
            pydantic_model(name="This is a really long name")

        pydantic_model(name="short name")


class TestNumericColumn(TestCase):
    """
    Numeric and Decimal are the same - so we'll just Numeric.
    """

    def test_numeric_digits(self):
        class Movie(Table):
            box_office = Numeric(digits=(5, 1))

        pydantic_model = create_pydantic_model(table=Movie)

        with self.assertRaises(ValidationError):
            # This should fail as there are too much numbers after the decimal
            # point
            pydantic_model(box_office=decimal.Decimal("1.11"))

        with self.assertRaises(ValidationError):
            # This should fail as there are too much numbers in total
            pydantic_model(box_office=decimal.Decimal("11111.1"))

        pydantic_model(box_office=decimal.Decimal("1.0"))


class TestSecretColumn(TestCase):
    def test_secret_param(self):
        class TopSecret(Table):
            confidential = Secret()

        pydantic_model = create_pydantic_model(table=TopSecret)
        self.assertEqual(
            pydantic_model.schema()["properties"]["confidential"]["extra"][
                "secret"
            ],
            True,
        )


class TestColumnHelpText(TestCase):
    """
    Make sure that columns with `help_text` attribute defined have the
    relevant text appear in the schema.
    """

    def test_help_text_present(self):

        help_text = "In millions of US dollars."

        class Movie(Table):
            box_office = Numeric(digits=(5, 1), help_text=help_text)

        pydantic_model = create_pydantic_model(table=Movie)
        self.assertEqual(
            pydantic_model.schema()["properties"]["box_office"]["extra"][
                "help_text"
            ],
            help_text,
        )


class TestTableHelpText(TestCase):
    """
    Make sure that tables with `help_text` attribute defined have the
    relevant text appear in the schema.
    """

    def test_help_text_present(self):

        help_text = "Movies which were released in cinemas."

        class Movie(Table, help_text=help_text):
            name = Varchar()

        pydantic_model = create_pydantic_model(table=Movie)
        self.assertEqual(
            pydantic_model.schema()["help_text"],
            help_text,
        )


class TestJSONColumn(TestCase):
    def test_default(self):
        class Movie(Table):
            meta = JSON()
            meta_b = JSONB()

        pydantic_model = create_pydantic_model(table=Movie)

        json_string = '{"code": 12345}'

        model_instance = pydantic_model(meta=json_string, meta_b=json_string)
        self.assertEqual(model_instance.meta, json_string)
        self.assertEqual(model_instance.meta_b, json_string)

    def test_deserialize_json(self):
        class Movie(Table):
            meta = JSON()
            meta_b = JSONB()

        pydantic_model = create_pydantic_model(
            table=Movie, deserialize_json=True
        )

        json_string = '{"code": 12345}'
        output = {"code": 12345}

        model_instance = pydantic_model(meta=json_string, meta_b=json_string)
        self.assertEqual(model_instance.meta, output)
        self.assertEqual(model_instance.meta_b, output)

    def test_validation(self):
        class Movie(Table):
            meta = JSON()
            meta_b = JSONB()

        for deserialize_json in (True, False):
            pydantic_model = create_pydantic_model(
                table=Movie, deserialize_json=deserialize_json
            )

            json_string = "error"

            with self.assertRaises(pydantic.ValidationError):
                pydantic_model(meta=json_string, meta_b=json_string)


class TestDefaultColumn(TestCase):
    def test_default(self):
        class Monitor(Table):
            refresh_rate = Integer(default=144)
            resolution = Varchar(required=True)

        pydantic_model = create_pydantic_model(Monitor)

        assert pydantic_model.schema()["required"] == ["resolution"]

        pydantic_instance = pydantic_model(resolution="1440*2560")

        assert pydantic_instance.refresh_rate == 144
        assert pydantic_instance.resolution == "1440*2560"

    def test_default_factory(self):
        class Monitor(Table):
            refresh_rate = Integer(required=True)
            resolution = Varchar(default=lambda: "1920*1080")

        pydantic_model = create_pydantic_model(Monitor)

        assert pydantic_model.schema()["required"] == ["refresh_rate"]

        pydantic_instance = pydantic_model(refresh_rate=60)

        assert pydantic_instance.refresh_rate == 60
        assert pydantic_instance.resolution == "1920*1080"

    def test_override_default(self):
        class Monitor(Table):
            refresh_rate = Integer(default=240)
            resolution = Varchar(default=lambda: "1440*2560")

        pydantic_model = create_pydantic_model(Monitor)

        assert not pydantic_model.schema().get("required")

        pydantic_instance = pydantic_model(
            refresh_rate=60,
            resolution="1080*1920",
        )

        assert pydantic_instance.refresh_rate == 60
        assert pydantic_instance.resolution == "1080*1920"
