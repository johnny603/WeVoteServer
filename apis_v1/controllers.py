# apis_v1/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.http import HttpResponse
from exception.models import handle_exception
from import_export_google_civic.models import fetch_google_civic_election_id_for_voter_id
from follow.models import FOLLOW_IGNORE, FOLLOWING, STOP_FOLLOWING
import json
from organization.models import Organization, OrganizationManager
from organization.controllers import organization_follow_all, organization_save
from voter.models import fetch_voter_id_from_voter_device_link, Voter, VoterManager, VoterDeviceLinkManager
from voter_guide.models import VoterGuideList
import wevote_functions.admin
from wevote_functions.models import convert_to_int, \
    is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def organization_count():
    organization_count_all = 0
    try:
        organization_list_all = Organization.objects.all()
        organization_count_all = organization_list_all.count()
        success = True

        # We will want to cache a json file and only refresh it every couple of seconds (so it doesn't become
        # a bottle neck as we grow)
    except Exception as e:
        exception_message = "organizationCount: Unable to count list of Organizations from db."
        handle_exception(e, logger=logger, exception_message=exception_message)
        success = False

    json_data = {
        'success': success,
        'organization_count': organization_count_all,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def organization_follow(voter_device_id, organization_id):
    """
    Save that the voter wants to follow this org
    :param voter_device_id:
    :param organization_id:
    :return:
    """
    return organization_follow_all(voter_device_id, organization_id, follow_kind=FOLLOWING)


def organization_stop_following(voter_device_id, organization_id):
    """
    Save that the voter wants to stop following this org
    :param voter_device_id:
    :param organization_id:
    :return:
    """
    return organization_follow_all(voter_device_id, organization_id, follow_kind=STOP_FOLLOWING)


def organization_follow_ignore(voter_device_id, organization_id):
    """
    Save that the voter wants to ignore this org
    :param voter_device_id:
    :param organization_id:
    :return:
    """
    return organization_follow_all(voter_device_id, organization_id, follow_kind=FOLLOW_IGNORE)


# We retrieve from only one of the two possible variables
def organization_retrieve(organization_id, organization_we_vote_id):
    organization_id = convert_to_int(organization_id)

    we_vote_id = organization_we_vote_id.strip()
    if not positive_value_exists(organization_id) and not positive_value_exists(organization_we_vote_id):
        json_data = {
            'status': "ORGANIZATION_RETRIEVE_BOTH_IDS_MISSING",
            'success': False,
            'organization_id': organization_id,
            'organization_we_vote_id': organization_we_vote_id,
            'organization_name': '',
            'organization_email': '',
            'organization_website': '',
            'organization_twitter_handle': '',
            'organization_facebook': '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    organization_manager = OrganizationManager()
    results = organization_manager.retrieve_organization(organization_id, organization_we_vote_id)

    if results['organization_found']:
        organization = results['organization']
        json_data = {
            'success': True,
            'status': results['status'],
            'organization_id': organization.id,
            'organization_we_vote_id': organization.we_vote_id,
            'organization_name':
                organization.organization_name if positive_value_exists(organization.organization_name) else '',
            'organization_website': organization.organization_website if positive_value_exists(
                organization.organization_website) else '',
            'organization_twitter_handle':
                organization.organization_twitter_handle if positive_value_exists(
                    organization.organization_twitter_handle) else '',
            'organization_email':
                organization.organization_email if positive_value_exists(organization.organization_email) else '',
            'organization_facebook':
                organization.organization_facebook if positive_value_exists(organization.organization_facebook) else '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        json_data = {
            'status': results['status'],
            'success': False,
            'organization_id': organization_id,
            'organization_we_vote_id': we_vote_id,
            'organization_name': '',
            'organization_email': '',
            'organization_website': '',
            'organization_twitter_handle': '',
            'organization_facebook': '',
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')


def organization_save_for_api(voter_device_id, organization_id, organization_we_vote_id, organization_name,
                              organization_email, organization_website,
                              organization_twitter_handle, organization_facebook, organization_image):
    organization_id = convert_to_int(organization_id)
    organization_we_vote_id = organization_we_vote_id.strip()

    existing_unique_identifier_found = positive_value_exists(organization_id) \
        or positive_value_exists(organization_we_vote_id)
    new_unique_identifier_found = positive_value_exists(organization_twitter_handle) \
        or positive_value_exists(organization_website)
    unique_identifier_found = existing_unique_identifier_found or new_unique_identifier_found
    # We must have one of these: twitter_handle or website, AND organization_name
    required_variables_for_new_entry = positive_value_exists(organization_twitter_handle) \
        or positive_value_exists(organization_website) and positive_value_exists(organization_name)
    if not unique_identifier_found:
        results = {
            'status': "ORGANIZATION_REQUIRED_UNIQUE_IDENTIFIER_VARIABLES_MISSING",
            'success': False,
            'organization_id': organization_id,
            'organization_we_vote_id': organization_we_vote_id,
            'new_organization_created': False,
            'organization_name': organization_name,
            'organization_email': organization_email,
            'organization_website': organization_website,
            'organization_twitter_handle': organization_twitter_handle,
            'organization_facebook': organization_facebook,
        }
        return results
    elif not existing_unique_identifier_found and not required_variables_for_new_entry:
        results = {
            'status': "NEW_ORGANIZATION_REQUIRED_VARIABLES_MISSING",
            'success': False,
            'organization_id': organization_id,
            'organization_we_vote_id': organization_we_vote_id,
            'new_organization_created': False,
            'organization_name': organization_name,
            'organization_email': organization_email,
            'organization_website': organization_website,
            'organization_twitter_handle': organization_twitter_handle,
            'organization_facebook': organization_facebook,
        }
        return results

    save_results = organization_save(organization_id, organization_we_vote_id, organization_name, organization_email,
                                     organization_website, organization_twitter_handle, organization_facebook,
                                     organization_image)

    if save_results['success']:
        organization = save_results['organization']
        results = {
            'success':                      True,
            'status':                       save_results['status'],
            'voter_device_id':              voter_device_id,
            'organization_id':              organization.id,
            'organization_we_vote_id':      organization.we_vote_id,
            'new_organization_created':     save_results['new_organization_created'],
            'organization_name':
                organization.organization_name if positive_value_exists(organization.organization_name) else '',
            'organization_email':
                organization.organization_email if positive_value_exists(organization.organization_email) else '',
            'organization_website':
                organization.organization_website if positive_value_exists(organization.organization_website) else '',
            'organization_twitter_handle':
                organization.organization_twitter_handle if positive_value_exists(
                    organization.organization_twitter_handle) else '',
            'organization_facebook':
                organization.organization_facebook if positive_value_exists(organization.organization_facebook) else '',
        }
        return results
    else:
        results = {
            'success':                  False,
            'status':                   save_results['status'],
            'voter_device_id':          voter_device_id,
            'organization_id':          organization_id,
            'organization_we_vote_id':  organization_we_vote_id,
            'new_organization_created': save_results['new_organization_created'],
            'organization_name':        organization_name,
            'organization_email':       organization_email,
            'organization_website':     organization_website,
            'organization_twitter_handle': organization_twitter_handle,
            'organization_facebook':    organization_facebook,
        }
        return results


def voter_count():
    voter_count_all = 0
    try:
        voter_list_all = Voter.objects.all()
        # In future, add a filter to only show voters who have actually done something
        # voter_list = voter_list.filter(id=voter_id)
        voter_count_all = voter_list_all.count()
        success = True

        # We will want to cache a json file and only refresh it every couple of seconds (so it doesn't become
        # a bottle neck as we grow)
    except Exception as e:
        exception_message = "voterCount: Unable to count list of Voters from db."
        handle_exception(e, logger=logger, exception_message=exception_message)
        success = False

    json_data = {
        'success': success,
        'voter_count': voter_count_all,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_create(voter_device_id):
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        return HttpResponse(json.dumps(results['json_data']), content_type='application/json')

    voter_id = 0
    # Make sure a voter record hasn't already been created for this
    existing_voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if existing_voter_id:
        json_data = {
            'status': "VOTER_ALREADY_EXISTS",
            'success': False,
            'voter_device_id': voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    # Create a new voter and return the id
    voter_manager = VoterManager()
    results = voter_manager.create_voter()

    if results['voter_created']:
        voter = results['voter']

        # Now save the voter_device_link
        voter_device_link_manager = VoterDeviceLinkManager()
        results = voter_device_link_manager.save_new_voter_device_link(voter_device_id, voter.id)

        if results['voter_device_link_created']:
            voter_device_link = results['voter_device_link']
            voter_id_found = True if voter_device_link.voter_id > 0 else False

            if voter_id_found:
                voter_id = voter_device_link.voter_id

    if voter_id:
        json_data = {
            'status': "VOTER_CREATED",
            'success': False,
            'voter_device_id': voter_device_id,
            'voter_id': voter_id,  # We may want to remove this after initial testing
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')
    else:
        json_data = {
            'status': "VOTER_NOT_CREATED",
            'success': False,
            'voter_device_id': voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_guides_to_follow_retrieve(voter_device_id, google_civic_election_id):
    # Get voter_id from the voter_device_id so we can figure out which voter_guides to offer
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status': 'ERROR_GUIDES_TO_FOLLOW_NO_VOTER_DEVICE_ID',
            'success': False,
            'voter_device_id': voter_device_id,
            'voter_guides': [],
            'google_civic_election_id': google_civic_election_id,
        }
        results = {
            'success': False,
            'google_civic_election_id': 0,  # Force the reset of google_civic_election_id cookie
            'json_data': json_data,
        }
        return results

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': "ERROR_GUIDES_TO_FOLLOW_VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success': False,
            'voter_device_id': voter_device_id,
            'voter_guides': [],
            'google_civic_election_id': google_civic_election_id,
        }
        results = {
            'success': False,
            'google_civic_election_id': 0,  # Force the reset of google_civic_election_id cookie
            'json_data': json_data,
        }
        return results

    # If the google_civic_election_id was found cached in a cookie and passed in, use that
    # If not, fetch it for this voter by looking in the BallotItem table
    if not positive_value_exists(google_civic_election_id):
        google_civic_election_id = fetch_google_civic_election_id_for_voter_id(voter_id)

    voter_guide_list = []
    voter_guides = []
    try:
        voter_guide_list_object = VoterGuideList()
        results = voter_guide_list_object.retrieve_voter_guides_for_election(google_civic_election_id)
        success = results['success']
        status = results['status']
        voter_guide_list = results['voter_guide_list']

    except Exception as e:
        status = 'FAILED voter_guides_to_follow_retrieve, retrieve_voter_guides_for_election ' \
                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        handle_exception(e, logger=logger, exception_message=status)
        success = False

    if success:
        for voter_guide in voter_guide_list:
            one_voter_guide = {
                'google_civic_election_id': voter_guide.google_civic_election_id,
                'voter_guide_owner_type': voter_guide.voter_guide_owner_type,
                'organization_we_vote_id': voter_guide.organization_we_vote_id,
                'public_figure_we_vote_id': voter_guide.public_figure_we_vote_id,
                'owner_voter_id': voter_guide.owner_voter_id,
                'last_updated': voter_guide.last_updated.strftime('%Y-%m-%d %H:%M'),
            }
            voter_guides.append(one_voter_guide.copy())

        if len(voter_guides):
            json_data = {
                'status': 'VOTER_GUIDES_TO_FOLLOW_RETRIEVED',
                'success': True,
                'voter_device_id': voter_device_id,
                'voter_guides': voter_guides,
                'google_civic_election_id': google_civic_election_id,
            }
        else:
            json_data = {
                'status': 'NO_VOTER_GUIDES_FOUND',
                'success': True,
                'voter_device_id': voter_device_id,
                'voter_guides': voter_guides,
                'google_civic_election_id': google_civic_election_id,
            }

        results = {
            'success': success,
            'google_civic_election_id': google_civic_election_id,
            'json_data': json_data,
        }
        return results
    else:
        json_data = {
            'status': status,
            'success': False,
            'voter_device_id': voter_device_id,
            'voter_guides': [],
            'google_civic_election_id': google_civic_election_id,
        }

        results = {
            'success': False,
            'google_civic_election_id': 0,  # Force the reset of google_civic_election_id cookie
            'json_data': json_data,
        }
        return results


def voter_retrieve_list_for_api(voter_device_id):
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        results2 = {
            'success': False,
            'json_data': results['json_data'],
        }
        return results2

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if voter_id > 0:
        voter_manager = VoterManager()
        results = voter_manager.retrieve_voter_by_id(voter_id)
        if results['voter_found']:
            voter_id = results['voter_id']
    else:
        # If we are here, the voter_id could not be found from the voter_device_id
        json_data = {
            'status': "VOTER_NOT_FOUND_FROM_DEVICE_ID",
            'success': False,
            'voter_device_id': voter_device_id,
        }
        results = {
            'success': False,
            'json_data': json_data,
        }
        return results

    if voter_id:
        voter_list = Voter.objects.all()
        voter_list = voter_list.filter(id=voter_id)

        if len(voter_list):
            results = {
                'success': True,
                'voter_list': voter_list,
            }
            return results

    # Trying to mimic the Google Civic error codes scheme
    errors_list = [
        {
            'domain':  "TODO global",
            'reason':  "TODO reason",
            'message':  "TODO Error message here",
            'locationType':  "TODO Error message here",
            'location':  "TODO location",
        }
    ]
    error_package = {
        'errors':   errors_list,
        'code':     400,
        'message':  "Error message here",
    }
    json_data = {
        'error': error_package,
        'status': "VOTER_ID_COULD_NOT_BE_RETRIEVED",
        'success': False,
        'voter_device_id': voter_device_id,
    }
    results = {
        'success': False,
        'json_data': json_data,
    }
    return results
