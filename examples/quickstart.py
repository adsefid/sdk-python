"""Send a single SMS with the sync AdsefidClient.

Usage:
    ADSEFID_API_KEY=... python examples/quickstart.py
"""

from __future__ import annotations

import os
import sys

from adsefid import (
    AdsefidApiError,
    AdsefidClient,
    AdsefidRateLimitError,
    AdsefidValidationError,
    LineSelector,
    SendSingleSmsRequest,
)


def main() -> None:
    api_key = os.environ["ADSEFID_API_KEY"]

    with AdsefidClient(api_key=api_key) as client:
        try:
            result = client.sms.send_single(
                SendSingleSmsRequest(
                    receptor=os.environ.get("ADSEFID_RECEPTOR", "989120000000"),
                    line_number=os.environ.get("ADSEFID_LINE_NUMBER", "983000"),
                    line_selector=LineSelector.BULK_SERVICE_SEND_BASED,  # see the README
                    message="Hello from adsefid",
                )
            )
        except AdsefidValidationError as exc:
            print(f"invalid request, no network call was made: {exc}", file=sys.stderr)
            return
        except AdsefidRateLimitError as exc:
            print(f"rate limited: code={exc.code} name={exc.name}", file=sys.stderr)
            return
        except AdsefidApiError as exc:
            print(
                f"API error: code={exc.code} name={exc.name} "
                f"http_status_code={exc.http_status_code} details={exc.details}",
                file=sys.stderr,
            )
            return

        print(f"sent message_id={result.message_id} status={result.status} cost={result.cost}")


if __name__ == "__main__":
    main()
