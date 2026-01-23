#!/bin/bash

# Android Build Preparation and Verification Script
# This script helps prepare the mobile app for Android Google Play submission

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check file exists
file_exists() {
    [ -f "$1" ]
}

# Function to check directory exists
dir_exists() {
    [ -d "$1" ]
}

echo "================================"
echo "Android Build Preparation Script"
echo "================================"
echo ""

# Check prerequisites
print_info "Checking prerequisites..."

# Check if we're in the mobile directory
if [ ! -f "package.json" ] || [ ! -f "app.json" ]; then
    print_error "Must run this script from the mobile directory"
    exit 1
fi

# Check Node.js version
print_info "Checking Node.js version..."
if command_exists node; then
    NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1-2)
    REQUIRED_VERSION="18.18"
    if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$NODE_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
        print_success "Node.js version $NODE_VERSION (>= $REQUIRED_VERSION)"
    else
        print_error "Node.js version $NODE_VERSION is too old (>= $REQUIRED_VERSION required)"
        exit 1
    fi
else
    print_error "Node.js is not installed"
    exit 1
fi

# Check npm
print_info "Checking npm..."
if command_exists npm; then
    NPM_VERSION=$(npm -v)
    print_success "npm version $NPM_VERSION"
else
    print_error "npm is not installed"
    exit 1
fi

# Check EAS CLI
print_info "Checking EAS CLI..."
if command_exists eas; then
    EAS_VERSION=$(eas --version | grep 'eas-cli' | awk '{print $2}')
    print_success "EAS CLI version $EAS_VERSION"
else
    print_warning "EAS CLI is not installed"
    print_info "Install with: npm install -g eas-cli"
    read -p "Install EAS CLI now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        npm install -g eas-cli
        print_success "EAS CLI installed"
    else
        print_error "EAS CLI is required to continue"
        exit 1
    fi
fi

# Check if logged into Expo
print_info "Checking Expo login status..."
if eas whoami >/dev/null 2>&1; then
    EXPO_USER=$(eas whoami)
    print_success "Logged in as: $EXPO_USER"
else
    print_warning "Not logged into Expo"
    print_info "Login with: eas login"
    read -p "Login to Expo now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        eas login
        if [ $? -eq 0 ]; then
            print_success "Logged into Expo"
        else
            print_error "Failed to login to Expo"
            exit 1
        fi
    else
        print_error "Must be logged into Expo to build"
        exit 1
    fi
fi

echo ""
print_info "Verifying project files..."

# Check required files
REQUIRED_FILES=(
    "app.json"
    "eas.json"
    "package.json"
    "tsconfig.json"
    "babel.config.js"
)

for file in "${REQUIRED_FILES[@]}"; do
    if file_exists "$file"; then
        print_success "$file exists"
    else
        print_error "$file is missing"
        exit 1
    fi
done

# Check required directories
REQUIRED_DIRS=(
    "src"
    "assets"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if dir_exists "$dir"; then
        print_success "$dir/ exists"
    else
        print_error "$dir/ is missing"
        exit 1
    fi
done

# Check asset files
print_info "Checking asset files..."
ASSETS=(
    "assets/icon.png"
    "assets/splash.png"
    "assets/adaptive-icon.png"
    "assets/favicon.png"
    "assets/notification-icon.png"
)

for asset in "${ASSETS[@]}"; do
    if file_exists "$asset"; then
        # Check file dimensions (basic check)
        SIZE=$(file "$asset" | grep -o '[0-9]* x [0-9]*' || echo "0 x 0")
        print_success "$asset exists ($SIZE)"
    else
        print_warning "$asset is missing (placeholder may be in place)"
    fi
done

echo ""
print_info "Validating configuration files..."

# Validate app.json
print_info "Validating app.json..."
if python3 -c "import json; json.load(open('app.json'))" 2>/dev/null; then
    print_success "app.json is valid JSON"

    # Check key fields
    PACKAGE_NAME=$(python3 -c "import json; print(json.load(open('app.json'))['expo']['android']['package'])" 2>/dev/null || echo "")
    if [ "$PACKAGE_NAME" = "com.sattva.streamer" ]; then
        print_success "Package name: $PACKAGE_NAME"
    else
        print_error "Package name mismatch: $PACKAGE_NAME (expected: com.sattva.streamer)"
        print_info "Package name MUST match Google Play Console"
    fi

    VERSION=$(python3 -c "import json; print(json.load(open('app.json'))['expo']['version'])" 2>/dev/null || echo "")
    print_success "Version: $VERSION"

    VERSION_CODE=$(python3 -c "import json; print(json.load(open('app.json'))['expo']['android']['versionCode'])" 2>/dev/null || echo "")
    print_success "Version Code: $VERSION_CODE"
else
    print_error "app.json is not valid JSON"
    exit 1
fi

# Validate eas.json
print_info "Validating eas.json..."
if python3 -c "import json; json.load(open('eas.json'))" 2>/dev/null; then
    print_success "eas.json is valid JSON"

    # Check if credentials are configured
    if python3 -c "import json; data=json.load(open('eas.json')); print('submit' in data and 'production' in data['submit'] and 'android' in data['submit']['production'])" 2>/dev/null; then
        SERVICE_ACCOUNT_PATH=$(python3 -c "import json; print(json.load(open('eas.json'))['submit']['production']['android'].get('serviceAccountKeyPath', ''))" 2>/dev/null || echo "")

        if [ -n "$SERVICE_ACCOUNT_PATH" ]; then
            if file_exists "$SERVICE_ACCOUNT_PATH"; then
                print_success "Service account key exists: $SERVICE_ACCOUNT_PATH"

                # Check if file is valid JSON
                if python3 -c "import json; json.load(open('$SERVICE_ACCOUNT_PATH'))" 2>/dev/null; then
                    print_success "Service account key is valid JSON"
                else
                    print_error "Service account key is not valid JSON"
                fi
            else
                print_warning "Service account key not found: $SERVICE_ACCOUNT_PATH"
                print_info "Automatic submission will not work without this key"
                print_info "See: docs/android-google-play-submission-guide.md"
            fi
        else
            print_warning "Service account key path not configured in eas.json"
            print_info "Add 'serviceAccountKeyPath' to enable automatic submission"
        fi
    else
        print_warning "Android submit configuration not found in eas.json"
        print_info "Add submit configuration for automatic submission to Google Play"
    fi
else
    print_error "eas.json is not valid JSON"
    exit 1
fi

echo ""
print_info "Checking documentation files..."

DOCS=(
    "docs/app-store-listing.md"
    "docs/privacy-policy.md"
    "docs/android-google-play-submission-guide.md"
    "docs/android-google-play-checklist.md"
    "docs/ASSETS_GUIDE.md"
)

for doc in "${DOCS[@]}"; do
    if file_exists "$doc"; then
        print_success "$doc exists"
    else
        print_warning "$doc is missing"
    fi
done

echo ""
print_info "TypeScript type checking..."

# Run TypeScript check
if npx tsc --noEmit 2>&1 | grep -q "error TS"; then
    print_warning "TypeScript errors detected"
    print_info "Run 'npm run type-check' to see details"
else
    print_success "No TypeScript errors"
fi

echo ""
print_info "Checking dependencies..."

# Check if node_modules exists
if dir_exists "node_modules"; then
    print_success "node_modules exists"
else
    print_warning "node_modules not found"
    print_info "Install dependencies with: npm install"
    read -p "Install dependencies now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        npm install
        if [ $? -eq 0 ]; then
            print_success "Dependencies installed"
        else
            print_error "Failed to install dependencies"
            exit 1
        fi
    else
        print_error "Dependencies must be installed before building"
        exit 1
    fi
fi

echo ""
print_info "Git status check..."

# Check git status
if command_exists git; then
    if git status --porcelain | grep -q " M"; then
        print_warning "Uncommitted changes detected"
        print_info "It's recommended to commit changes before building"
        git status --short
    else
        print_success "Working directory is clean"
    fi
else
    print_warning "Git not found, skipping status check"
fi

echo ""
echo "================================"
print_success "Preparation complete!"
echo "================================"
echo ""

# Summary
echo "Next Steps:"
echo ""
echo "1. Create app in Google Play Console:"
echo "   - Visit: https://play.google.com/console"
echo "   - Package name: com.sattva.streamer"
echo "   - See: docs/android-google-play-submission-guide.md"
echo ""
echo "2. Configure Google Play service account:"
echo "   - Navigate to: Setup → API access"
echo "   - Link Google Cloud project"
echo "   - Create service account"
echo "   - Generate JSON key"
echo "   - Place key file in: mobile/google-service-account-key.json"
echo "   - Update eas.json with service account path"
echo ""
echo "3. Build the app:"
echo "   - Run: eas build --platform android --profile production"
echo ""
echo "4. Monitor build progress:"
echo "   - Check the build URL provided by EAS"
echo "   - Wait ~20-30 minutes for build to complete"
echo ""
echo "5. Submit to Google Play:"
echo "   - If service account key is configured: automatic"
echo "   - Otherwise: upload AAB manually to Google Play Console"
echo ""
echo "6. Configure internal testing:"
echo "   - Add testers (up to 100)"
echo "   - Share opt-in link"
echo "   - Install and verify on test device"
echo ""
echo "For detailed instructions, see:"
echo "   - docs/android-google-play-submission-guide.md"
echo "   - docs/android-google-play-checklist.md"
echo ""

# Check if service account key exists
if [ -n "$SERVICE_ACCOUNT_PATH" ] && file_exists "$SERVICE_ACCOUNT_PATH"; then
    print_success "Service account key configured - automatic submission enabled"
    echo ""
else
    print_warning "Service account key not configured - manual submission required"
    echo ""
fi

read -p "Ready to start the build now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Starting Android build..."
    echo ""
    eas build --platform android --profile production
else
    print_info "Build cancelled. Run this script again when ready."
fi
