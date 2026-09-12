"""Enumerations defined by the adsefid.com Web Service API (doc v1.13.0, section 3)."""

from enum import Enum, IntEnum


class LineSelector(IntEnum):
    """See doc section 3.1."""

    PROMOTIONAL_SEND_BASED = 0
    PROMOTIONAL_DELIVER_BASED = 1
    BULK_SERVICE_SEND_BASED = 2
    BULK_SERVICE_DELIVER_BASED = 3
    CUSTOMER_CLUB_SERVICE_SEND_BASED = 4
    CUSTOMER_CLUB_SERVICE_DELIVER_BASED = 5


class WebServiceMessageStatus(IntEnum):
    """See doc section 3.2. Values 1000-1999."""

    SCHEDULED = 1000
    SENDING = 1001
    DELIVERED = 1002
    UNDELIVERED = 1003
    CANCELED = 1004
    SENT_TO_OPERATOR = 1005
    BLACKLISTED = 1006
    PROVIDER_ERROR = 1007
    PENDING_APPROVAL = 1008
    REJECTED = 1009
    INVALID_SENDER = 1010
    INVALID_ATTACHMENT = 1011
    FORBIDDEN_WORD = 1012
    LINK_NOT_ALLOWED = 1013
    INVALID_RECEIVER = 1014
    UNDELIVERABLE = 1015
    SENDER_LIMIT_REACHED = 1016
    UNKNOWN = 1999


class WebServiceResponseCode(IntEnum):
    """See doc section 3.4. Values 2000-2047."""

    INTERNAL_ERROR = 2000
    INVALID_PLAN = 2001
    LINE_NOT_FOUND = 2002
    TOO_MANY_RECEPTORS = 2003
    INVALID_LINE = 2004
    INVALID_API_KEY = 2005
    IP_NOT_ALLOWED = 2006
    DUPLICATE_LOCAL_ID = 2007
    USER_INFORMATION_NOT_FOUND = 2008
    EMPTY_RECEPTORS = 2009
    INVALID_RECEPTORS = 2010
    EMPTY_BODY = 2011
    EMPTY_LINE = 2012
    EMPTY_MESSAGE = 2013
    INVALID_RECEPTOR = 2014
    EMPTY_RECEPTOR = 2015
    MESSAGE_TOO_LARGE = 2016
    INVALID_LINE_SELECTOR = 2017
    UNAUTHORIZED = 2018
    INVALID_SEND_RANGE = 2019
    ALL_RECEPTORS_BLACKLISTED = 2020
    MESSAGE_CONTAINS_FORBIDDEN_WORDS = 2021
    NOT_ENOUGH_CREDIT = 2022
    DUPLICATE_TAG = 2023
    INVALID_PARAMETER = 2024
    RECEPTOR_BLACKLISTED = 2025
    INVALID_LINK_IN_MESSAGE = 2026
    TEMPLATE_NOT_APPROVED = 2027
    INVALID_TEMPLATE_PARAMETER = 2028
    INVALID_LOCAL_IDS = 2029
    EMPTY_LOCAL_IDS = 2030
    EMPTY_MESSAGE_IDS = 2031
    INVALID_SMS_TYPE = 2032
    LINE_NOT_ACTIVE = 2033
    LINE_EXPIRED = 2034
    MESSAGE_LIMIT_REACHED = 2035
    REQUEST_LIMIT_REACHED = 2036
    INVALID_SEND_TIME = 2037
    INVALID_EXPIRY = 2038
    INVALID_TEMPLATE_ID = 2039
    PROFILE_NOT_FOUND = 2040
    PROFILE_EXPIRED = 2041
    FILE_NOT_FOUND = 2042
    INVALID_FILE = 2043
    ACCESS_DENIED = 2044
    REJECTED = 2045
    INVALID_MESSAGE_IDS = 2046
    FILE_TOO_LARGE = 2047


class TemplateState(str, Enum):
    """See doc section 3.5."""

    PENDING_APPROVAL = "pendingapproval"
    APPROVED = "approved"
    REJECTED = "rejected"


class TemplateParameterType(str, Enum):
    """See doc section 3.6.

    The doc's complete public set is {string, number}. The real server has
    been observed to also emit an undocumented "url" value; it is
    intentionally not exposed here pending a doc update.
    """

    STRING = "string"
    NUMBER = "number"


MESSAGE_STATUS_MIN = 1000
"""Lowest `WebServiceCode` value that is a message status (doc section 3.3)."""

ERROR_CODE_MIN = 2000
"""Lowest `WebServiceCode` value that is an error code (doc section 3.3)."""


def parse_message_status(value: int) -> tuple[WebServiceMessageStatus | None, int]:
    """Permissively parse a WebServiceMessageStatus, tolerating unknown future codes.

    Returns (enum_member_or_None, raw_int).
    """
    try:
        return WebServiceMessageStatus(value), value
    except ValueError:
        return None, value


def parse_response_code(value: int) -> tuple[WebServiceResponseCode | None, int]:
    """Permissively parse a WebServiceResponseCode, tolerating unknown future codes.

    Returns (enum_member_or_None, raw_int).
    """
    try:
        return WebServiceResponseCode(value), value
    except ValueError:
        return None, value
