from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("messaging", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            """
            CREATE
                OR REPLACE FUNCTION delete_orphan_message()
                RETURNS TRIGGER
                LANGUAGE plpgsql AS
            $$
            BEGIN
                -- When an event with message gets deleted, check if any other
                -- events remain to that given message. If not, delete the
                -- message itself.
                DELETE
                FROM messaging_message message
                WHERE message.id = OLD.message_id
                  AND NOT EXISTS(SELECT 1
                                 FROM messaging_event
                                 WHERE message_id = OLD.message_id);
                RETURN NULL;
            END;
            $$;

            CREATE
                OR REPLACE TRIGGER delete_orphan_messages
                AFTER DELETE
                ON messaging_event
                FOR EACH ROW
            EXECUTE FUNCTION delete_orphan_message();
            """,
            reverse_sql="DROP FUNCTION IF EXISTS delete_orphan_message CASCADE;",
        )
    ]
