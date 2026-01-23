#!/usr/bin/env bash
# =============================================================================
# Cross-Platform Build Validation Script
# Detects case-sensitivity issues and path problems for cross-platform builds
# =============================================================================

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Error counters
ERRORS=0
WARNINGS=0
CHECKS_PASSED=0

# Directories to check
FRONTEND_DIR="${FRONTEND_DIR:-./frontend}"
PROJECT_ROOT="${PROJECT_ROOT:-.}"

# Logging functions
log_info() { printf "${BLUE}%s${NC}\n" "$*"; }
log_success() { printf "${GREEN}✓ %s${NC}\n" "$*"; ((CHECKS_PASSED++)); }
log_warning() { printf "${YELLOW}⚠ %s${NC}\n" "$*"; ((WARNINGS++)); }
log_error() { printf "${RED}✗ %s${NC}\n" "$*"; ((ERRORS++)); }

print_header() {
    echo ""
    log_info "═══════════════════════════════════════════════════════════════"
    log_info "$1"
    log_info "═══════════════════════════════════════════════════════════════"
    echo ""
}

print_section() {
    echo ""
    log_info "▶ $1"
    echo ""
}

# Detect OS
detect_os() {
    case "$(uname -s)" in
        Linux*)     OS="Linux" ;;
        Darwin*)    OS="macOS" ;;
        CYGWIN*|MINGW*|MSYS*) OS="Windows" ;;
        *)          OS="Unknown" ;;
    esac
    export OS
}

# Check for duplicate files with different case (case-sensitivity issues)
check_case_sensitivity_duplicates() {
    print_section "Checking for case-sensitivity conflicts..."

    if [ ! -d "$FRONTEND_DIR" ]; then
        log_warning "Frontend directory not found: $FRONTEND_DIR"
        return 0
    fi

    # Create a temporary file to store lowercase filenames
    local tmp_file=$(mktemp)
    trap 'rm -f "$tmp_file"' RETURN

    # Find all files and convert to lowercase for comparison
    find "$FRONTEND_DIR" -type f -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/dist/*" -not -path "*/.next/*" | while read -r file; do
        # Get the relative path from frontend dir
        rel_path="${file#$FRONTEND_DIR/}"
        # Convert to lowercase
        echo "$(echo "$rel_path" | tr '[:upper:]' '[:lower:]')|$rel_path" >> "$tmp_file"
    done

    # Check for duplicates (same lowercase path but different original paths)
    local duplicates=$(sort "$tmp_file" | uniq -d -f0 | cut -d'|' -f1 | uniq)

    if [ -n "$duplicates" ]; then
        log_error "Found files that differ only by case (will break on case-insensitive systems):"
        echo "$duplicates" | while read -r lowercase_path; do
            grep "|.*$" "$tmp_file" | grep "|$lowercase_path$" | sed 's/^/  /' | while read -r conflict; do
                original_path=$(echo "$conflict" | cut -d'|' -f2)
                log_error "  - $original_path"
            done
        done
    else
        log_success "No case-sensitivity conflicts found"
    fi
}

# Check for inconsistent import casing
check_import_casing_consistency() {
    print_section "Checking import statement casing consistency..."

    if [ ! -d "$FRONTEND_DIR" ]; then
        log_warning "Frontend directory not found: $FRONTEND_DIR"
        return 0
    fi

    # Find all TypeScript/JavaScript files
    local found_issues=0

    while IFS= read -r -d '' file; do
        # Check for imports with different casing than actual files
        # This is a basic heuristic check

        # Extract import statements (basic regex)
        local imports=$(grep -E "from ['\"](\.\.?/[^'\"]+)['\"]" "$file" 2>/dev/null | grep -oE "from ['\"]\.\.?/[^'\"]+['\"]" | sed "s/from ['\"]//g" | sed "s/['\"]//g" || true)

        if [ -n "$imports" ]; then
            echo "$imports" | while read -r import_path; do
                # Skip node_modules and complex imports
                if echo "$import_path" | grep -qE "node_modules|\.css|\.scss|\.svg|\.png|\.jpg|\.jpeg"; then
                    continue
                fi

                # Resolve the import path relative to the file
                local file_dir=$(dirname "$file")
                local resolved_path="$file_dir/$import_path"

                # Check for .tsx, .ts, .jsx, .js extensions
                local found_file=""
                for ext in tsx ts jsx js; do
                    if [ -f "${resolved_path}.${ext}" ]; then
                        found_file="${resolved_path}.${ext}"
                        break
                    fi
                done

                # Also check for index files
                if [ -z "$found_file" ] && [ -d "$resolved_path" ]; then
                    for ext in tsx ts jsx js; do
                        if [ -f "${resolved_path}/index.${ext}" ]; then
                            found_file="${resolved_path}/index.${ext}"
                            break
                        fi
                    done
                fi

                # If we found a file, check if the actual file exists with different casing
                if [ -n "$found_file" ]; then
                    # On case-insensitive systems, we need to be more careful
                    # On case-sensitive systems, the file just won't exist if cased wrong
                    if [ ! -e "$found_file" ]; then
                        # Try to find the actual file
                        local actual_file=$(find "$file_dir" -iname "$(basename "$import_path").*" -type f 2>/dev/null | head -1)
                        if [ -n "$actual_file" ]; then
                            log_error "In $file:"
                            log_error "  Import path may have wrong casing: $import_path"
                            log_error "  Actual file: $(basename "$actual_file")"
                            found_issues=1
                        fi
                    fi
                fi
            done
        fi
    done < <(find "$FRONTEND_DIR/src" -type f \( -name "*.tsx" -o -name "*.ts" -o -name "*.jsx" -o -name "*.js" \) -print0 2>/dev/null || true)

    if [ "$found_issues" -eq 0 ]; then
        log_success "No import casing inconsistencies detected"
    fi
}

# Check for problematic path lengths (Windows has 260 character limit)
check_path_lengths() {
    print_section "Checking path lengths..."

    local max_length=0
    local max_path=""
    local warning_threshold=200  # Warn at 200 characters
    local error_threshold=250    # Error at 250 characters (Windows limit is 260)
    local long_paths=0
    local very_long_paths=0

    if [ ! -d "$FRONTEND_DIR" ]; then
        log_warning "Frontend directory not found: $FRONTEND_DIR"
        return 0
    fi

    while IFS= read -r file; do
        local length=${#file}
        if [ "$length" -gt "$max_length" ]; then
            max_length=$length
            max_path="$file"
        fi

        if [ "$length" -gt "$error_threshold" ]; then
            log_error "Path exceeds $error_threshold characters (will break on Windows):"
            log_error "  Length: $length characters"
            log_error "  Path: $file"
            ((very_long_paths++))
        elif [ "$length" -gt "$warning_threshold" ]; then
            log_warning "Path is very long ($length characters, may cause issues on Windows):"
            log_warning "  $file"
            ((long_paths++))
        fi
    done < <(find "$FRONTEND_DIR" -type f -not -path "*/node_modules/*" -not -path "*/.git/*" 2>/dev/null || true)

    echo "  Longest path: $max_length characters"
    echo "  $max_path"

    if [ "$very_long_paths" -eq 0 ] && [ "$long_paths" -eq 0 ]; then
        log_success "All paths are within safe length limits"
    fi
}

# Check for problematic characters in filenames
check_filename_characters() {
    print_section "Checking for problematic filename characters..."

    local found_issues=0

    if [ ! -d "$FRONTEND_DIR" ]; then
        log_warning "Frontend directory not found: $FRONTEND_DIR"
        return 0
    fi

    # Characters that are problematic on Windows
    local windows_forbidden='<>:"|?*'
    local problematic_chars='[<>:"|?*\x00-\x1f]'

    while IFS= read -r file; do
        local filename=$(basename "$file")

        # Check for Windows-forbidden characters
        if echo "$filename" | grep -qE "[$windows_forbidden]"; then
            log_error "Filename contains characters forbidden on Windows:"
            log_error "  $file"
            found_issues=1
        fi

        # Check for control characters
        if echo "$filename" | grep -qP '\x00-\x1f'; then
            log_error "Filename contains control characters:"
            log_error "  $file"
            found_issues=1
        fi

        # Check for trailing spaces (problematic on Windows)
        if [[ "$filename" =~ \ $ ]]; then
            log_warning "Filename ends with space (problematic on Windows):"
            log_warning "  $file"
        fi

        # Check for trailing dot (problematic on Windows)
        if [[ "$filename" =~ \.$ ]]; then
            log_warning "Filename ends with dot (problematic on Windows):"
            log_warning "  $file"
        fi
    done < <(find "$FRONTEND_DIR" -type f -not -path "*/node_modules/*" -not -path "*/.git/*" 2>/dev/null || true)

    if [ "$found_issues" -eq 0 ]; then
        log_success "No problematic filename characters found"
    fi
}

# Check for hardcoded absolute paths in source code
check_hardcoded_paths() {
    print_section "Checking for hardcoded absolute paths..."

    local found_issues=0

    if [ ! -d "$FRONTEND_DIR" ]; then
        log_warning "Frontend directory not found: $FRONTEND_DIR"
        return 0
    fi

    # Patterns that indicate hardcoded paths
    local patterns=(
        "C:\\\\"
        "D:\\\\"
        "/home/"
        "/Users/"
        "/opt/"
        "/var/"
        "/tmp/"
    )

    while IFS= read -r file; do
        for pattern in "${patterns[@]}"; do
            if grep -qF "$pattern" "$file" 2>/dev/null; then
                log_warning "Possible hardcoded absolute path found:"
                log_warning "  File: $file"
                log_warning "  Pattern: $pattern"
                found_issues=1
            fi
        done
    done < <(find "$FRONTEND_DIR/src" -type f \( -name "*.tsx" -o -name "*.ts" -o -name "*.jsx" -o -name "*.js" \) -print0 2>/dev/null || true)

    if [ "$found_issues" -eq 0 ]; then
        log_success "No hardcoded absolute paths detected"
    fi
}

# Check for case-sensitive import mismatches in frontend
check_frontend_import_case() {
    print_section "Checking frontend import path casing..."

    if [ ! -d "$FRONTEND_DIR/src" ]; then
        log_warning "Frontend src directory not found: $FRONTEND_DIR/src"
        return 0
    fi

    local found_issues=0

    # Check imports in TypeScript/JavaScript files
    while IFS= read -r -d '' file; do
        # Extract import statements with relative paths
        grep -ohE "from ['\"]\.{1,2}/[^'\"]+['\"]" "$file" 2>/dev/null | while read -r import_stmt; do
            # Clean up the import path
            import_path=$(echo "$import_stmt" | sed "s/from ['\"]//g" | sed "s/['\"]//g")

            # Skip non-relative imports and certain file types
            if ! echo "$import_path" | grep -qE "^\.{1,2}/"; then
                continue
            fi

            if echo "$import_path" | grep -qE "\.(css|scss|svg|png|jpg|jpeg|gif|ico|woff|woff2|ttf|eot)$"; then
                continue
            fi

            # Get the directory of the current file
            file_dir=$(dirname "$file")
            import_dir="$file_dir/$(dirname "$import_path")"
            import_basename=$(basename "$import_path")

            # Try to find the actual file (case-insensitive search)
            actual_file=""
            for ext in tsx ts jsx js; do
                candidate="$import_dir/${import_basename}.${ext}"
                if [ -f "$candidate" ]; then
                    actual_file="$candidate"
                    break
                fi
            done

            # Check for index file
            if [ -z "$actual_file" ] && [ -d "$import_dir/$import_basename" ]; then
                for ext in tsx ts jsx js; do
                    candidate="$import_dir/${import_basename}/index.${ext}"
                    if [ -f "$candidate" ]; then
                        actual_file="$candidate"
                        break
                    fi
                done
            fi

            # If we found a file, check if the import statement matches the actual file case
            if [ -n "$actual_file" ]; then
                actual_basename=$(basename "$actual_file" | sed 's/\.[^.]*$//')

                # Compare case-insensitively first
                if [ "${import_basename,,}" != "${actual_basename,,}" ]; then
                    continue
                fi

                # Now check if the cases are different
                if [ "$import_basename" != "$actual_basename" ]; then
                    log_error "Import path casing mismatch in $file:"
                    log_error "  Imported as: $import_path"
                    log_error "  Actual file:  $actual_basename"
                    found_issues=1
                fi
            fi
        done
    done < <(find "$FRONTEND_DIR/src" -type f \( -name "*.tsx" -o -name "*.ts" -o -name "*.jsx" -o -name "*.js" \) -print0 2>/dev/null || true)

    if [ "$found_issues" -eq 0 ]; then
        log_success "No import path casing mismatches found"
    fi
}

# Check if running on case-sensitive filesystem
check_filesystem_case_sensitivity() {
    print_section "Checking filesystem case-sensitivity..."

    local test_dir="/tmp/case-test-$$"
    local case_sensitive=0

    if mkdir "$test_dir" 2>/dev/null; then
        if touch "$test_dir/test" 2>/dev/null; then
            if touch "$test_dir/TEST" 2>/dev/null; then
                # Both files exist - case-sensitive
                case_sensitive=1
                rm -f "$test_dir/test" "$test_dir/TEST"
            else
                # Second file failed to create - case-insensitive
                case_sensitive=0
            fi
        fi
        rmdir "$test_dir" 2>/dev/null || true
    fi

    if [ "$case_sensitive" -eq 1 ]; then
        echo "  Current filesystem: Case-sensitive (Linux/macOS default)"
        echo "  Note: Files may behave differently on Windows (case-insensitive)"
    else
        echo "  Current filesystem: Case-insensitive (Windows default)"
        log_warning "Development on case-insensitive filesystem may hide case-sensitivity bugs"
    fi
}

# Main execution
main() {
    print_header "Cross-Platform Build Validation"

    detect_os
    echo "Running on: $OS"
    echo "Frontend directory: $FRONTEND_DIR"
    echo "Project root: $PROJECT_ROOT"

    # Run all checks
    check_filesystem_case_sensitivity
    check_case_sensitivity_duplicates
    check_import_casing_consistency
    check_frontend_import_case
    check_path_lengths
    check_filename_characters
    check_hardcoded_paths

    # Print summary
    print_header "Validation Summary"
    echo ""
    echo "Checks passed: $CHECKS_PASSED"
    echo "Warnings:       $WARNINGS"
    echo "Errors:         $ERRORS"
    echo ""

    if [ $ERRORS -gt 0 ]; then
        log_error "Cross-platform validation FAILED with $ERRORS error(s)"
        echo ""
        echo "Please fix the errors above to ensure compatibility across platforms."
        exit 1
    elif [ $WARNINGS -gt 0 ]; then
        log_warning "Cross-platform validation PASSED with $WARNINGS warning(s)"
        echo ""
        echo "Consider addressing the warnings for better cross-platform compatibility."
        exit 0
    else
        log_success "Cross-platform validation PASSED"
        echo ""
        echo "All checks passed! The build is compatible across Linux, macOS, and Windows."
        exit 0
    fi
}

# Run main function
main "$@"
