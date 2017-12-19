# Webhooks for external integrations.
import logging
from typing import Any, Dict, Iterable, Optional, Text

from django.http import HttpRequest, HttpResponse
from django.utils.translation import ugettext as _

from zerver.decorator import api_key_only_webhook_view
from zerver.lib.actions import check_send_stream_message
from zerver.lib.request import REQ, has_request_variables
from zerver.lib.response import json_error, json_success
from zerver.lib.validator import check_dict, check_string
from zerver.models import UserProfile, get_user_profile_by_email

PayloadType = Dict[str, Iterable[Dict[str, Any]]]

def get_agent(email):
    # type: (str) -> str

    # Groove webhook doesn't give us the name of the agent.
    # An agent is a person working for a business and most likely a member of Zulip community.
    # So we try to get the name from Zulip database.
    # If the user doesn't exist, we use the email as name.
    try:
        agent_name = get_user_profile_by_email(email).full_name
    except Exception as e:
        agent_name = email
    return agent_name


def format_groove_ticket_started_message(payload):
    # type: (PayloadType) -> str
    customer = payload['customer_name']
    ticket_number = payload['number']
    ticket_url = payload['app_url']
    message = payload['last_message_plain_text']
    title = payload['title']
    body_template = 'New ticket started for {customer}\n' \
                    '[Ticket #{number} - {subject}]({ticket_url})\n'\
                    '```quote\n' \
                    '{message}\n' \
                    '```'
    body = body_template.format(customer = customer,
                                number = ticket_number,
                                subject = title,
                                ticket_url = ticket_url,
                                message = message)
    return body

def format_groove_ticket_state_changed_message(payload):
    # type: (PayloadType) -> str
    customer = payload['ticket']['customer_name']
    ticket_number = payload['ticket_number']
    ticket_url = payload['app_url']
    state = payload['state']
    body_template = '[Ticket #{number}]({ticket_url}) to {customer} '
    body = body_template.format(customer = customer,
                                number = ticket_number,
                                ticket_url = ticket_url)
    if state == 'opened':
        body += 'has been marked as open'
    elif state == 'closed':
        body += 'has been closed'
    elif state == 'pending' or state == 'spam':
        body += 'has been marked as ' + state
    else:
        body = ''  # State not recognized, don't send anything.

    return body

def format_groove_customer_replied_message(payload):
    # type: (PayloadType) -> str
    customer_url = payload['links']['author']['href']
    email = customer_url.split('http://api.groovehq.com/v1/customers/')[1]
    ticket_url = payload['app_ticket_url']  # the url used to hyperlink to in the message

    ticket_link = payload['links']['ticket']['href']  # the link from which we extract ticket number
    ticket_number = ticket_link.split('http://api.groovehq.com/v1/tickets/')[1]

    message = payload['plain_text_body']
    # Splitting the url into list and getting the second item as ticket number.
    body_template = '{customer} has replied to [Ticket #{number}({ticket_url}) \n'\
                    '```quote\n' \
                    '{message}\n' \
                    '```'
    body = body_template.format(customer = email,
                                number = ticket_number,
                                ticket_url = ticket_url,
                                message = message)
    return body

def format_groove_agent_replied_message(payload):
    # type: (PayloadType) -> str

    customer_url = payload['links']['recipient']['href']
    customer_email = customer_url.split('http://api.groovehq.com/v1/customers/')[1]
    agent_url = payload['links']['author']['href']
    agent_email = agent_url.split('http://api.groovehq.com/v1/agents/')[1]
    agent = get_agent(agent_email)
    ticket_url = payload['app_ticket_url']  # the url used to hyperlink to in the message

    ticket_link = payload['links']['ticket']['href']  # the link from which we extract ticket number
    ticket_number = ticket_link.split('http://api.groovehq.com/v1/tickets/')[1]

    message = payload['plain_text_body']
    # Splitting the url into list and getting the second item as ticket number.
    body_template = '{agent} has replied to [Ticket #{number}]({ticket_url}) for {customer}\n'\
                    '```quote\n' \
                    '{message}\n' \
                    '```'
    body = body_template.format(agent = agent,
                                customer = customer_email,
                                number = ticket_number,
                                ticket_url = ticket_url,
                                message = message)
    return body

def format_groove_note_added_message(payload):
    # type: (PayloadType) -> str

    agent_link = payload['links']['author']['href']
    agent_email = agent_link.split('http://api.groovehq.com/v1/agents/')[1]
    agent = get_agent(agent_email)
    ticket_link = payload['links']['ticket']['href']  # the link from which we extract ticket number
    ticket_number = ticket_link.split('http://api.groovehq.com/v1/tickets/')[1]
    ticket_url = payload['app_ticket_url']
    note = payload['plain_text_body']
    body_template = '{agent} has left a note on [Ticket #{number}]({ticket_url}) \n'\
                    '```quote\n' \
                    '{message}\n' \
                    '```'
    body = body_template.format(agent = agent,
                                number = ticket_number,
                                ticket_url = ticket_url,
                                message = note)
    return body


def format_groove_ticket_assigned_message(payload):
    # type: (PayloadType) -> str

    agent_email = payload['assignee']
    agent = get_agent(agent_email)

    ticket_number = payload['number']
    ticket_url = payload['app_url']
    group = payload['assigned_group']
    subject = payload['title']
    body_template = '[Ticket #{number} - {subject}]({ticket_url}) has been assigned to:\n'
    body = body_template.format(number = ticket_number,
                                ticket_url = ticket_url,
                                subject = subject)
    if not agent_email and not group:
        # this shouldn't happen, but just in case.
        return ''
    elif not agent_email and group:
        body += '* Group : {group}'.format(group=group)
    elif agent_email and not group:
        body += '* Agent : {agent}'.format(agent=agent)
    elif agent_email and group:
        body += '* Agent : {agent}\n* Group : {group}'.format(group=group, agent=agent)
    return body

def get_ticket_number(payload):
    # type: (PayloadType) -> int
    if payload.get('number', None):
        return payload['number']
    elif payload.get('ticket_number', None):
        return payload['ticket_number']
    else:
        ticket_url = payload['links']['ticket']['href']
        number = ticket_url.split('http://api.groovehq.com/v1/tickets/')[1]
        return number

@api_key_only_webhook_view('Groove')
@has_request_variables
def api_groove_webhook(request, user_profile,
                       payload=REQ(argument_type='body'), stream=REQ(default='test'),
                       topic=REQ(default='test integration')):
    # type: (HttpRequest, UserProfile, Dict[str, Iterable[Dict[str, Any]]], Text, Optional[Text]) -> HttpResponse
    META = (request.META)
    event = ''
    try:
        event = META['HTTP_X_GROOVE_EVENT']
    except KeyError:
        logging.error('No event header with Groove payload')
        return json_error()
    content = ''
    try:
        # construct the body of the message
        if event == 'ticket_started':
            content = format_groove_ticket_started_message(payload)
        if event == 'customer_replied':
            content = format_groove_customer_replied_message(payload)
        elif event == 'note_added':
            content = format_groove_note_added_message(payload)
        elif event == 'ticket_assigned':
            content = format_groove_ticket_assigned_message(payload)
        elif event == 'agent_replied':
            content = format_groove_agent_replied_message(payload)
        elif event == 'ticket_state_changed':
            content = format_groove_ticket_state_changed_message(payload)
    except KeyError as e:
        logging.error('Required key not found : ' + e.args[0])

    ticket = str(get_ticket_number(payload))

    # send the message
    check_send_stream_message(user_profile, request.client, stream, 'Ticket #'+ticket, content)
    return json_success()
