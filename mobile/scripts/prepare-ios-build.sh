#!/bin/bash

# iOS Build Preparation and Verification Script
# This script helps prepare the mobile app for iOS TestFlight submission

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
echo "iOS Build Preparation Script"
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
    BUNDLE_ID=$(python3 -c "import json; print(json.load(open('app.json'))['expo']['ios']['bundleIdentifier'])" 2>/dev/null || echo "")
    if [ "$BUNDLE_ID" = "com.sattva.streamer" ]; then
        print_success "Bundle ID: $BUNDLE_ID"
    else
        print_error "Bundle ID mismatch: $BUNDLE_ID (expected: com.sattva.streamer)"
    fi

    VERSION=$(python3 -c "import json; print(json.load(open('app.json'))['expo']['version'])" 2>/dev/null || echo "")
    print_success "Version: $VERSION"

    BUILD_NUMBER=$(python3 -c "import json; print(json.load(open('app.json'))['expo']['ios']['buildNumber'])" 2>/dev/null || echo "")
    print_success "Build Number: $BUILD_NUMBER"
else
    print_error "app.json is not valid JSON"
    exit 1
fi

# Validate eas.json
print_info "Validating eas.json..."
if python3 -c "import json; json.load(open('eas.json'))" 2>/dev/null; then
    print_success "eas.json is valid JSON"

    # Check if credentials are still placeholders
    APPLE_ID=$(python3 -c "import json; print(json.load(open('eas.json'))['submit']['production']['ios']['appleId'])" 2>/dev/null || echo "")
    if [[ "$APPLE_ID" == *"example.com"* ]] || [[ "$APPLE_ID" == *"your-"* ]]; then
        print_warning "Apple ID is still a placeholder: $APPLE_ID"
        print_info "Update eas.json with your Apple credentials before building"
    else
        print_success "Apple ID configured: $APPLE_ID"
    fi

    ASC_APP_ID=$(python3 -c "import json; print(json.load(open('eas.json'))['submit']['production']['ios']['ascAppId'])" 2>/dev/null || echo "")
    if [[ "$ASC_APP_ID" == *"YOUR_"* ]]; then
        print_warning "ASC App ID is still a placeholder"
        print_info "Update eas.json with your App Store Connect App ID"
    else
        print_success "ASC App ID configured"
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
    "docs/ios-testflight-submission-guide.md"
    "docs/ios-testflight-checklist.md"
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
echo "1. Update eas.json with your Apple credentials:"
echo "   - appleId: Your Apple ID email"
echo "   - ascAppId: Your App Store Connect App ID"
echo "   - appleTeamId: Your Apple Team ID"
echo ""
echo "2. Create app in App Store Connect:"
echo "   - Visit: https://appstoreconnect.apple.com/"
echo "   - Bundle ID: com.sattva.streamer"
echo "   - See: docs/ios-testflight-submission-guide.md"
echo ""
echo "3. Build the app:"
echo "   - Run: eas build --platform ios --profile production"
echo ""
echo "4. Monitor build progress:"
echo "   - Check the build URL provided by EAS"
echo "   - Wait ~20-30 minutes for build to complete"
echo ""
echo "5. Submit to TestFlight:"
echo "   - Build will auto-submit if credentials are correct"
echo "   - Or submit manually via App Store Connect"
echo ""
echo "For detailed instructions, see:"
echo "   - docs/ios-testflight-submission-guide.md"
echo "   - docs/ios-testflight-checklist.md"
echo ""

read -p "Ready to start the build now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Starting iOS build..."
    echo ""
    eas build --platform ios --profile production
else
    print_info "Build cancelled. Run this script again when ready."
fi
