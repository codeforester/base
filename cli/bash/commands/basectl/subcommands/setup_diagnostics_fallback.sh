#!/usr/bin/env bash

[[ -n "${_base_setup_diagnostics_fallback_sourced:-}" ]] && return 0
_base_setup_diagnostics_fallback_sourced=1
readonly _base_setup_diagnostics_fallback_sourced

# Keep JSON diagnostics available when the Python renderer cannot start. This
# file is sourced by setup_common.sh after the check-result helpers; the
# functions it calls are resolved when the fallback is invoked.
source "$BASE_HOME/cli/bash/commands/basectl/subcommands/inspection_json.sh"

setup_diagnostics_fallback_payload_status() {
    local payload="$1"

    if [[ "$payload" == *'"status":"error"'* || "$payload" == *'"status": "error"'* ]]; then
        printf '%s\n' error
    elif [[ "$payload" == *'"status":"warn"'* || "$payload" == *'"status": "warn"'* ]]; then
        printf '%s\n' warn
    else
        printf '%s\n' ok
    fi
}

setup_diagnostics_fallback_check_item() {
    local finding_id metadata name="$1" status="$2" message="$3" recovery="$4"

    metadata="$(setup_base_check_metadata "$name")"
    IFS=$'\t' read -r _ finding_id _ <<<"$metadata"
    [[ "$status" == ok ]] && recovery=""
    printf '{"id":'
    base_inspection_json_string "$finding_id"
    printf ',"status":'
    base_inspection_json_string "$status"
    printf ',"name":'
    base_inspection_json_string "$name"
    printf ',"message":'
    base_inspection_json_string "$message"
    printf ',"fix":'
    base_inspection_json_string "$recovery"
    printf '}'
}

setup_diagnostics_fallback_project_venv_item() {
    local status="$1" message="$2" recovery="$3"

    [[ "$status" == ok ]] && recovery=""
    printf '{"id":"BASE-P050","status":'
    base_inspection_json_string "$status"
    printf ',"name":"project_virtualenv","message":'
    base_inspection_json_string "$message"
    printf ',"fix":'
    base_inspection_json_string "$recovery"
    printf '}'
}

setup_diagnostics_fallback_append_item() {
    local output_name="$1" list="$2" item="$3"

    if [[ "$list" == "[]" ]]; then
        printf -v "$output_name" '%s' "[$item]"
    elif [[ "$list" == \[*\] ]]; then
        printf -v "$output_name" '%s' "${list%]},$item]"
    else
        printf -v "$output_name" '%s' "[$item]"
    fi
}

setup_diagnostics_fallback_record_check() {
    local checked_at="" path="" project="" status="" tmp_path

    while (($#)); do
        case "$1" in
            --project)
                project="${2:-}"
                shift 2
                ;;
            --status)
                status="${2:-}"
                shift 2
                ;;
            --checked-at)
                checked_at="${2:-}"
                shift 2
                ;;
            --output-path)
                path="${2:-}"
                shift 2
                ;;
            *)
                base_std_fatal_error "Unsupported diagnostics fallback argument '$1'."
                ;;
        esac
    done

    case "$status" in
        ok|warn|error) ;;
        *) base_std_fatal_error "Invalid diagnostics record status '$status'." ;;
    esac
    [[ -n "$project" && -n "$checked_at" && -n "$path" ]] ||
        base_std_fatal_error "Diagnostics record fallback requires project, status, checked-at, and output-path."

    mkdir -p -- "$(dirname -- "$path")" || return 1
    tmp_path="${path}.tmp.$$"
    {
        printf '{\n  "schema_version": 1,\n  "project": '
        base_inspection_json_string "$project"
        printf ',\n  "command": "basectl check",\n  "status": '
        base_inspection_json_string "$status"
        printf ',\n  "checked_at": '
        base_inspection_json_string "$checked_at"
        printf '\n}\n'
    } >"$tmp_path" && mv -- "$tmp_path" "$path"
}

setup_diagnostics_fallback_json() {
    local command="${1:-}"
    shift || true

    case "$command" in
        record-check)
            setup_diagnostics_fallback_record_check "$@"
            return $?
            ;;
        project-venv-check-json|project-venv-doctor-json)
            local fix="" message="" precheck_json="[]" project="" status="" item_json output_json aggregate_status
            while (($#)); do
                case "$1" in
                    --project)
                        project="${2:-}"
                        shift 2
                        ;;
                    --status)
                        status="${2:-}"
                        shift 2
                        ;;
                    --message)
                        message="${2:-}"
                        shift 2
                        ;;
                    --fix)
                        fix="${2:-}"
                        shift 2
                        ;;
                    --precheck-json)
                        precheck_json="${2:-[]}"
                        shift 2
                        ;;
                    *)
                        base_std_fatal_error "Unsupported diagnostics fallback argument '$1'."
                        ;;
                esac
            done
            item_json="$(setup_diagnostics_fallback_project_venv_item "$status" "$message" "$fix")"
            setup_diagnostics_fallback_append_item output_json "$precheck_json" "$item_json"
            aggregate_status="$(setup_diagnostics_fallback_payload_status "$precheck_json")"
            aggregate_status="$(setup_merge_diagnostic_status "$aggregate_status" "$status")"
            if [[ "$command" == project-venv-check-json ]]; then
                printf '{"schema_version": 1, "status": '
                base_inspection_json_string "$aggregate_status"
                printf ', "project": '
                base_inspection_json_string "$project"
                printf ', "checks": %s}\n' "$output_json"
            else
                printf '%s\n' "$output_json"
            fi
            [[ "$aggregate_status" != error ]]
            return $?
            ;;
        check-json|doctor-json)
            local checked_at="" embedded_key embedded_payload project="" record_path=""
            local result_file status="ok" item_json output_json
            local check_names=() check_statuses=() check_messages=() check_fixes=()
            local result_files=() embedded_keys=() embedded_values=() item_key="checks"
            local i

            [[ "$command" == doctor-json ]] && item_key="findings"
            while (($#)); do
                case "$1" in
                    --project)
                        project="${2:-}"
                        shift 2
                        ;;
                    --check|--finding)
                        check_names+=("${2:-}")
                        check_statuses+=("${3:-}")
                        check_messages+=("${4:-}")
                        check_fixes+=("${5:-}")
                        shift 5
                        ;;
                    --check-result-file|--finding-result-file)
                        result_files+=("${2:-}")
                        shift 2
                        ;;
                    --embedded-payload)
                        embedded_keys+=("${2:-}")
                        embedded_values+=("${3:-}")
                        shift 3
                        ;;
                    --record-path)
                        record_path="${2:-}"
                        shift 2
                        ;;
                    --checked-at)
                        checked_at="${2:-}"
                        shift 2
                        ;;
                    *)
                        base_std_fatal_error "Unsupported diagnostics fallback argument '$1'."
                        ;;
                esac
            done

            output_json='[]'
            for ((i = 0; i < ${#check_names[@]}; i++)); do
                item_json="$(setup_diagnostics_fallback_check_item "${check_names[$i]}" "${check_statuses[$i]}" "${check_messages[$i]}" "${check_fixes[$i]}")"
                setup_diagnostics_fallback_append_item output_json "$output_json" "$item_json"
                status="$(setup_merge_diagnostic_status "$status" "${check_statuses[$i]}")"
            done
            for result_file in "${result_files[@]}"; do
                setup_parse_check_result_file "$result_file"
                item_json="$(setup_diagnostics_fallback_check_item \
                    "$_BASE_SETUP_PARSED_CHECK_NAME" \
                    "$_BASE_SETUP_PARSED_CHECK_STATUS" \
                    "$_BASE_SETUP_PARSED_CHECK_MESSAGE" \
                    "$_BASE_SETUP_PARSED_CHECK_RECOVERY")"
                setup_diagnostics_fallback_append_item output_json "$output_json" "$item_json"
                status="$(setup_merge_diagnostic_status "$status" "$_BASE_SETUP_PARSED_CHECK_STATUS")"
            done
            for ((i = 0; i < ${#embedded_keys[@]}; i++)); do
                embedded_key="${embedded_keys[$i]}"
                embedded_payload="${embedded_values[$i]}"
                status="$(setup_merge_diagnostic_status "$status" "$(setup_diagnostics_fallback_payload_status "$embedded_payload")")"
            done

            printf '{"schema_version": 1, "status": '
            base_inspection_json_string "$status"
            if [[ -n "$project" ]]; then
                printf ', "project": '
                base_inspection_json_string "$project"
            fi
            printf ', "%s": %s' "$item_key" "$output_json"
            for ((i = 0; i < ${#embedded_keys[@]}; i++)); do
                embedded_key="${embedded_keys[$i]}"
                embedded_payload="${embedded_values[$i]}"
                printf ', '
                base_inspection_json_string "$embedded_key"
                printf ': %s' "$embedded_payload"
            done
            printf '}\n'

            if [[ -n "$record_path" && -n "$project" && -n "$checked_at" && "$command" == check-json ]]; then
                setup_diagnostics_fallback_record_check \
                    --project "$project" \
                    --status "$status" \
                    --checked-at "$checked_at" \
                    --output-path "$record_path" || return 1
            fi
            [[ "$status" != error ]]
            return $?
            ;;
        *)
            base_std_fatal_error "Python is required to render diagnostics command '$command'."
            ;;
    esac
}
