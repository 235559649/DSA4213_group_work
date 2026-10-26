"""Conservative failure classification from observed diagnostics, never code execution."""

from __future__ import annotations


_ENVIRONMENT_HINTS = (
    'command not found', 'no module named', 'could not resolve host',
    'no matching distribution found', 'permission denied', 'timed out',
)


def classify_failure(
    output: str,
    *,
    exception_type: str | None,
    exception_message: str,
    has_source_frames: bool,
    has_test_evidence: bool,
) -> dict:
    """Only narrow, explicit setup failures suppress mapped source candidates.

    Import/permission/network hints may be caused by project bugs. They are
    annotations, not a blanket veto on genuine source evidence. A configuration
    diagnosis requires a parsed terminal exception, not a phrase echoed by grep.
    """
    kind = (exception_type or '').rsplit('.', 1)[-1]
    message = exception_message.lower()
    # Once a terminal exception is known, unrelated grep/log/source text in
    # the same observation must not become environmental evidence for it.
    lowered = message if exception_type else output.lower()
    matched = [marker for marker in _ENVIRONMENT_HINTS if marker in lowered]
    configuration_rule = None
    django_type = exception_type in {kind, 'django.core.exceptions.' + kind}
    if (django_type and kind == 'ImproperlyConfigured' and 'settings are not configured' in message
            and ('django_settings_module' in message or 'settings.configure()' in message)):
        configuration_rule = 'django_settings_not_configured'
    elif django_type and kind == 'AppRegistryNotReady' and message in {"apps aren't loaded yet.", 'apps are not loaded yet.'}:
        configuration_rule = 'django_app_registry_not_ready'
    if configuration_rule:
        return {
            'category': 'environment_configuration', 'confidence': 'high',
            'environment_hint': True, 'suppress_ranking': True,
            'reason_code': configuration_rule,
            'evidence': [exception_type, exception_message],
        }
    if has_source_frames:
        category = 'ambiguous_environment_or_source' if matched else 'source_failure'
    elif matched:
        category = 'possible_environment_failure'
    elif has_test_evidence:
        category = 'test_failure_without_source'
    else:
        category = 'unclassified_failure'
    return {
        'category': category, 'confidence': 'low' if matched or not has_source_frames else 'medium',
        'environment_hint': bool(matched), 'suppress_ranking': False,
        'reason_code': 'environment_hint_only' if matched else 'observed_failure_evidence',
        'evidence': matched,
    }
