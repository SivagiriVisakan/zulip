from typing import Text
from zerver.lib.test_classes import WebhookTestCase

class GrooveHookTests(WebhookTestCase):
    STREAM_NAME = 'groove'
    URL_TEMPLATE = u"/api/v1/external/groove?api_key={api_key}&stream={stream}"

    def test_ticket_started(self) -> None:

        expected_subject = u"Ticket #1"
        expected_message = u'New ticket started for Test Name\n' \
                            '[Ticket #1 - Test Subject](https://testteam.groovehq.com/groove_client/tickets/68659446)\n' \
                            '```quote\n' \
                            'The content of the body goes here.\n' \
                            '```'
        self.send_and_test_stream_message('ticket_started', expected_subject, expected_message, content_type="application/x-www-form-urlencoded", **{'HTTP_X_GROOVE_EVENT':'ticket_started'})

    def test_ticket_state_changed(self) -> None:

        expected_subject = u"Ticket #776"
        expected_message_template = u'[Ticket #776](https://testteam.groovehq.com/groove_client/tickets/68667295) to someone ' \
                                     'has been marked as {}'

        expected_message = expected_message_template.format('pending')
        self.send_and_test_stream_message('ticket_state_changed_pending', expected_subject, expected_message, content_type="application/x-www-form-urlencoded", **{'HTTP_X_GROOVE_EVENT':'ticket_state_changed'})

        expected_message = expected_message_template.format('open')
        self.send_and_test_stream_message('ticket_state_changed_opened', expected_subject, expected_message, content_type="application/x-www-form-urlencoded", **{'HTTP_X_GROOVE_EVENT':'ticket_state_changed'})

        expected_message = expected_message_template.format('spam')
        self.send_and_test_stream_message('ticket_state_changed_spam', expected_subject, expected_message, content_type="application/x-www-form-urlencoded", **{'HTTP_X_GROOVE_EVENT':'ticket_state_changed'})

        expected_message = u'[Ticket #776](https://testteam.groovehq.com/groove_client/tickets/68667295) to someone ' \
                           'has been closed'
        self.send_and_test_stream_message('ticket_state_changed_closed', expected_subject, expected_message, content_type="application/x-www-form-urlencoded", **{'HTTP_X_GROOVE_EVENT':'ticket_state_changed'})

    def test_customer_replied(self) -> None:

        expected_subject = u"Ticket #440"
        expected_message = u'someone@example.com has replied to [Ticket #440(https://testteam.groovehq.com/groove_client/tickets/68666538) \n'\
                           '```quote\n' \
                           'Hello agent, thanks for getting back. This is how a reply from customer looks like.\n' \
                           '```'
        self.send_and_test_stream_message('customer_replied', expected_subject, expected_message, content_type="application/x-www-form-urlencoded", **{'HTTP_X_GROOVE_EVENT':'customer_replied'})

    def test_agent_replied(self) -> None:

        expected_subject = u"Ticket #776"
        expected_message = u'agent@example.com has replied to [Ticket #776](https://testteam.groovehq.com/groove_client/tickets/68667295) for someone@example.com\n'\
                           '```quote\n' \
                           'Hello , This is a reply from an agent to a ticket\n' \
                           '```'
        self.send_and_test_stream_message('agent_replied', expected_subject, expected_message, content_type="application/x-www-form-urlencoded", **{'HTTP_X_GROOVE_EVENT':'agent_replied'})

    def test_note_added(self) -> None:

        expected_subject = u"Ticket #776"
        expected_message = u'anotheragent@example.com has left a note on [Ticket #776](https://testteam.groovehq.com/groove_client/tickets/68667295) \n'\
                    '```quote\n' \
                    'This is a note added to  a ticket\n' \
                    '```'
        self.send_and_test_stream_message('note_added', expected_subject, expected_message, content_type="application/x-www-form-urlencoded", **{'HTTP_X_GROOVE_EVENT':'note_added'})

    def test_assigned(self) -> None:

        expected_subject = u"Ticket #9"
        expected_message_template = u'[Ticket #9 - Test Subject](https://testteam.groovehq.com/groove_client/tickets/68659446) has been assigned to:\n{}'

        expected_message = expected_message_template.format('* Agent : agent@example.com')
        self.send_and_test_stream_message('ticket_assigned_agent', expected_subject, expected_message, content_type="application/x-www-form-urlencoded", **{'HTTP_X_GROOVE_EVENT':'ticket_assigned'})

        expected_message = expected_message_template.format('* Agent : agent@example.com\n* Group : group2')
        self.send_and_test_stream_message('ticket_assigned', expected_subject, expected_message, content_type="application/x-www-form-urlencoded", **{'HTTP_X_GROOVE_EVENT':'ticket_assigned'})

        expected_message = expected_message_template.format('* Group : group2')
        self.send_and_test_stream_message('ticket_assigned_group', expected_subject, expected_message, content_type="application/x-www-form-urlencoded", **{'HTTP_X_GROOVE_EVENT':'ticket_assigned'})



    def get_body(self, fixture_name: Text) -> Text:
        return self.fixture_data("groove", fixture_name, file_type="json")
