"""Conservative failure classification from observed diagnostics, never code execution."""

from __future__ import annotations

from collections.abc import Collection


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


def classify_edit_failure(
    *, exception_type: str | None, terminal_locations: list[dict],
    modified_files: Collection[str], previously_valid_files: Collection[str],
) -> dict:
    """Suggest a recovery route only with caller-supplied validity evidence.

    Paths must already be repo-normalized. 'Modified' alone is not causation:
    require the actual terminal location in a currently syntax-invalid file AND
    evidence the same file was valid before the edit. Name/Import errors are
    never blanket-suppressed. This does not send a message or alter F itself.
    """
    syntax = exception_type in {
        'SyntaxError', 'IndentationError', 'TabError',
        'builtins.SyntaxError', 'builtins.IndentationError', 'builtins.TabError',
    }
    terminal = terminal_locations[-1] if terminal_locations else {}
    path = terminal.get('file')
    recovery = bool(syntax and path and path in modified_files and
        path in previously_valid_files and terminal.get('index_error_kind') == 'syntax_error' and
        terminal.get('index_error_line') == terminal.get('line'))
    return {'route': 'edit_recovery' if recovery else 'normal_analysis',
        'confidence': 'high' if recovery else 'unknown',
        'reason': 'modified_previously_valid_file_now_has_syntax_error' if recovery else 'insufficient_edit_causation',
        'file': path if recovery else None}
