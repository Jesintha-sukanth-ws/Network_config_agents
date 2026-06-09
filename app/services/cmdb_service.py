import logging
import requests

from pydantic import BaseModel

from config.settings import (
    SERVICENOW_INSTANCE,
    SERVICENOW_USERNAME,
    SERVICENOW_PASSWORD,
    SERVICENOW_SSL_VERIFY,
    SERVICENOW_TIMEOUT,
    CMDB_TABLE,
)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

def _coerce_field(value) -> str:
    """
    ServiceNow returns reference fields in different shapes depending on
    `sysparm_display_value`:
      - dict: {"display_value": "Cisco", "value": "<sys_id>", "link": "..."}
      - dict: {"value": "<sys_id>", "link": "..."}                   (raw)
      - str:  "Cisco"                                                (display)
      - "" / None when unset

    This helper normalizes any of these into a plain string. Empty / unset
    values become "".
    """

    if value is None:
        return ""

    if isinstance(value, dict):
        # Prefer human-readable display value, fall back to raw value
        return str(
            value.get("display_value")
            or value.get("value")
            or ""
        ).strip()

    return str(value).strip()


def _is_sys_id(value: str) -> bool:
    """A ServiceNow sys_id is a 32-char hex string."""
    return (
        isinstance(value, str)
        and len(value) == 32
        and all(c in "0123456789abcdef" for c in value.lower())
    )


# ---------------------------------------------------------------
# Models
# ---------------------------------------------------------------

class CMDBDevice(BaseModel):
    """
    Standardized device object used throughout orchestration.
    """

    device_name: str
    vendor: str
    model: str
    os_type: str
    management_host: str


# ---------------------------------------------------------------
# Service
# ---------------------------------------------------------------

class CMDBService:
    """
    Retrieves device information from ServiceNow CMDB.

    Designed to be tolerant of differing ServiceNow tenants:
    - reference fields can be returned as dicts or display strings
    - manufacturer may need a second lookup against core_company
    - the CMDB table is configurable via the CMDB_TABLE env var
    """

    REQUEST_FIELDS = (
        "name,"
        "model_number,"
        "ip_address,"
        "fqdn,"
        "u_os_type,"
        "os,"
        "manufacturer"
    )

    def __init__(self):
        self.base_url = SERVICENOW_INSTANCE.rstrip("/")
        self.auth = (
            SERVICENOW_USERNAME,
            SERVICENOW_PASSWORD,
        )

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def get_device(self, ci_sys_id: str) -> CMDBDevice:

        try:
            data = self._fetch_ci(ci_sys_id)

            if not data:
                raise ValueError(f"Device {ci_sys_id} not found in CMDB")

            device = self._map_device(data)

            logger.info("CMDB device loaded: %s", device.device_name)
            return device

        except requests.RequestException as e:
            logger.error("CMDB request failed: %s", e)
            raise

        except Exception as e:
            logger.exception("CMDB processing error: %s", e)
            raise

    def get_cmdb_data(self, ci_sys_id: str) -> CMDBDevice:
        """Backwards-compatible alias used by the orchestrator."""
        return self.get_device(ci_sys_id)

    # ------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------

    def _fetch_ci(self, ci_sys_id: str) -> dict:
        """
        Fetch a CI by sys_id from CMDB_TABLE. Falls back to the parent
        cmdb_ci table when the configured table does not contain the CI.
        Returns the raw `result` dict (or {} when nothing found).
        """

        for table in (CMDB_TABLE, "cmdb_ci"):
            if not table:
                continue

            url = f"{self.base_url}/api/now/table/{table}/{ci_sys_id}"

            params = {
                "sysparm_fields": self.REQUEST_FIELDS,
                "sysparm_display_value": "all",
            }

            response = requests.get(
                url,
                auth=self.auth,
                params=params,
                verify=SERVICENOW_SSL_VERIFY,
                timeout=SERVICENOW_TIMEOUT,
            )

            # 404 means "not in this table" — try the next one
            if response.status_code == 404:
                logger.debug(
                    "CI %s not found in table %s, trying fallback",
                    ci_sys_id,
                    table,
                )
                continue

            response.raise_for_status()

            data = response.json().get("result") or {}
            if data:
                logger.debug(
                    "CI %s loaded from table %s",
                    ci_sys_id,
                    table,
                )
                return data

        return {}

    def _resolve_manufacturer(self, raw_value) -> str:
        """
        ServiceNow stores manufacturer as a reference to core_company.
        When `sysparm_display_value=all` is used, the response contains
        both display_value and raw sys_id. If only a sys_id is present,
        do a second lookup to resolve the company name.
        """

        coerced = _coerce_field(raw_value)

        if coerced and not _is_sys_id(coerced):
            return coerced

        # Either we got back a raw sys_id only, or the dict contained
        # a usable value field — extract it deterministically
        sys_id = ""
        if isinstance(raw_value, dict):
            sys_id = str(raw_value.get("value") or "").strip()
        elif _is_sys_id(coerced):
            sys_id = coerced

        if not sys_id:
            return ""

        try:
            response = requests.get(
                f"{self.base_url}/api/now/table/core_company/{sys_id}",
                auth=self.auth,
                params={"sysparm_fields": "name"},
                verify=SERVICENOW_SSL_VERIFY,
                timeout=SERVICENOW_TIMEOUT,
            )
            if response.status_code == 200:
                return str(
                    response.json()
                    .get("result", {})
                    .get("name", "")
                ).strip()
        except requests.RequestException as e:
            logger.warning(
                "Manufacturer lookup failed for %s: %s",
                sys_id,
                e,
            )

        return ""

    def _map_device(self, data: dict) -> CMDBDevice:

        # Management endpoint (FQDN preferred, IP fallback)
        management_host = (
            _coerce_field(data.get("fqdn"))
            or _coerce_field(data.get("ip_address"))
        )

        if not management_host:
            raise ValueError("No management endpoint found in CMDB")

        # Manufacturer / vendor — may require a second hop
        vendor = self._resolve_manufacturer(data.get("manufacturer"))

        if not vendor:
            raise ValueError("Vendor missing in CMDB")

        # OS type — try the custom field first, then the standard one
        os_type = (
            _coerce_field(data.get("u_os_type"))
            or _coerce_field(data.get("os"))
        )

        if not os_type:
            raise ValueError(
                "OS type missing in CMDB "
                "(checked u_os_type and os fields)"
            )

        return CMDBDevice(
            device_name=_coerce_field(data.get("name")),
            vendor=vendor,
            model=_coerce_field(data.get("model_number")),
            os_type=os_type,
            management_host=management_host,
        )
