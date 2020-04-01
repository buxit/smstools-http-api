#!/usr/bin/env python

from __future__ import unicode_literals
from flask import current_app, request, jsonify
import xmltodict

from . import api_1_0
from .errors import bad_request
from .authentication import auth, verify_password

from .smstools import *

@api_1_0.route('/monitoring', methods=['GET'])
def monitoring_view():
    return jsonify({'monitoring': 'ok'})

@api_1_0.route('/sms/<kind>/', methods=['GET'])
@auth.login_required
def list_some_sms(kind):
    return list_some_sms(kind)

@api_1_0.route('/sms/<kind>/<message_id>', methods=['GET'])
@auth.login_required
def get_some_sms_view(kind, message_id):
    return get_some_sms(kind, message_id)

@api_1_0.route('/sms/<kind>/<message_id>', methods=['DELETE'])
@auth.login_required
def delete_sms_view(kind, message_id):
    return delete_some_sms(kind, message_id)

@api_1_0.route('/sms/outgoing', methods=['GET', 'POST'])
@auth.login_required
def outgoing_view():
    required_fields = ( 'mobiles', 'text' )

    if request.method == 'POST':
        request_object = request.json
    elif request.method == 'GET':
        request_object = {}
        mobiles = request.args.get('mobiles')
        text = request.args.get('text')
        if mobiles:
            request_object['mobiles'] = mobiles.replace(' ', '+').split(',')
        if text:
            request_object['text'] = text

    # Check input data
    if type(request_object) is not dict:
        return bad_request('Wrong JSON object')
    for required_field in required_fields:
        if required_field not in request_object:
            return bad_request('Missing required: {0}'.format(required_field))
    if type(request_object['mobiles']) is not list:
        return bad_request('mobiles is not array')
    if len(request_object['mobiles']) == 0:
        return bad_request('mobiles array is empty')

    try:
        unicode_str = unicode()
    except NameError:
        unicode_str = str()

    for mobile in request_object['mobiles']:
        if type(mobile) is not type(unicode_str):
            return bad_request('mobiles is not unicode')

    if type(request_object['text']) is not type(unicode_str):
        return bad_request('text is not unicode')

    queue = request_object.get('queue', current_app.config.get('DEFAULTQUEUE'))
    data = {
        'mobiles': request_object['mobiles'],
        'text': request_object['text'],
        'queue' : queue
    }

    result = send_sms(data)
    return jsonify(result)


def response_xml(code, description):
    import xml.etree.cElementTree as ET
    response = ET.Element("Response")
    ET.SubElement(response, "Code").text = str(code)
    ET.SubElement(response, "CodeDescription").text = description
    return ET.tostring(response, encoding="ISO-8859-1")

# xml_interface
@api_1_0.route('/', methods=['GET', 'POST'])
def outgoing_view_xml():

    required_fields = ( 'mobiles', 'text' )

    if request.method == 'POST':
        request_object = {}
        #print(request.data)
        try:
            xmldata = xmltodict.parse(request.data)
        except:
            return response_xml(4000, "ERR - BAD XML")

        #print(xmldata)

        if not verify_password(xmldata['Request']['AccountLogin']['#text'], xmldata['Request']['AccountPass']):
            return response_xml(4001, "ERR - INVALID CREDENTIALS")
        recipients = xmldata['Request']['Message']['Recipients']['Recipient']
        mobiles = []
        if isinstance(recipients, list):
            for recipient in recipients:
                mobiles.append('+' + recipient['#text'])
        else:
            mobiles.append('+' + recipients['#text'])
        text = xmldata['Request']['Message']['Text']['#text']
        if mobiles:
            request_object['mobiles'] = mobiles
        if text:
            request_object['text'] = bytes.fromhex(text.replace('20AC', '80')).decode('cp1252')
        #print(request_object)
    else:
        return response_xml(4000, "ERR - BAD XML")

    # Check input data
    for required_field in required_fields:
        if required_field not in request_object:
            return response_xml(4000, 'Missing required: {0}'.format(required_field))
    if len(request_object['mobiles']) == 0:
        return response_xml(4002, 'ERR – INVALID RECIPIENTS')

    try:
        unicode_str = unicode()
    except NameError:
        unicode_str = str()

    for mobile in request_object['mobiles']:
        if type(mobile) is not type(unicode_str):
            return response_xml(4005, 'mobiles is not unicode')

    if type(request_object['text']) is not type(unicode_str):
        return response_xml(4005, 'text is not unicode')

    queue = request_object.get('queue', current_app.config.get('DEFAULTQUEUE'))
    data = {
        'mobiles': request_object['mobiles'],
        'text': request_object['text'],
        'queue' : queue
    }

    result = send_sms(data)
    ok=0
    ids=[]
    for m in result['mobiles']:
        if result['mobiles'][m]['response'] == 'Ok':
            ok += 1
            ids.append(result['mobiles'][m]['message_id'])

    if ok == len(result['mobiles']):
        return response_xml(2001, 'OK - QUEUED')

    return response_xml(5000, 'ERR - NOT RECIPIENTS OK')
