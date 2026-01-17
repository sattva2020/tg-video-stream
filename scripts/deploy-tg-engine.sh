#!/bin/bash
# =============================================================================
# Deploy TG Engine to Dokploy
# =============================================================================
# This script prepares and triggers deployment of the AyuGram-based
# Telegram engine to Dokploy.
#
# Prerequisites:
# - Dokploy API key (get from Profile → API Tokens in Dokploy UI)
# - Project already created in Dokploy
# =============================================================================

set -e

# Configuration
DOKPLOY_URL="${DOKPLOY_URL:-https://dokploy.sattva-ai.top}"
DOKPLOY_API_KEY="${DOKPLOY_API_KEY:-}"
PROJECT_NAME="sattva-streamer"
APP_NAME="tg-engine"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=========================================="
echo "Deploy TG Engine to Dokploy"
echo -e "==========================================${NC}"

# Check API key
if [ -z "$DOKPLOY_API_KEY" ]; then
    echo -e "${RED}ERROR: DOKPLOY_API_KEY environment variable is not set${NC}"
    echo ""
    echo "To get your API key:"
    echo "1. Open Dokploy: ${DOKPLOY_URL}"
    echo "2. Go to Profile → API Tokens"
    echo "3. Create a new token"
    echo "4. Run: export DOKPLOY_API_KEY=your_token"
    echo ""
    exit 1
fi

echo -e "${YELLOW}Step 1: Getting project ID...${NC}"

# Get project ID
PROJECT_RESPONSE=$(curl -s -X GET "${DOKPLOY_URL}/api/project.all" \
    -H "x-api-key: ${DOKPLOY_API_KEY}" \
    -H "Content-Type: application/json")

PROJECT_ID=$(echo "$PROJECT_RESPONSE" | jq -r ".[] | select(.name==\"${PROJECT_NAME}\") | .projectId")

if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" = "null" ]; then
    echo -e "${RED}ERROR: Project '${PROJECT_NAME}' not found${NC}"
    echo "Available projects:"
    echo "$PROJECT_RESPONSE" | jq -r '.[].name'
    exit 1
fi

echo -e "${GREEN}Found project: ${PROJECT_NAME} (${PROJECT_ID})${NC}"

echo -e "${YELLOW}Step 2: Creating application...${NC}"

# Check if app already exists
APP_RESPONSE=$(curl -s -X GET "${DOKPLOY_URL}/api/application.all" \
    -H "x-api-key: ${DOKPLOY_API_KEY}" \
    -H "Content-Type: application/json")

APP_ID=$(echo "$APP_RESPONSE" | jq -r ".[] | select(.name==\"${APP_NAME}\") | .applicationId")

if [ -z "$APP_ID" ] || [ "$APP_ID" = "null" ]; then
    echo "Creating new application..."
    
    # Create application
    CREATE_RESPONSE=$(curl -s -X POST "${DOKPLOY_URL}/api/application.create" \
        -H "x-api-key: ${DOKPLOY_API_KEY}" \
        -H "Content-Type: application/json" \
        -d "{
            \"name\": \"${APP_NAME}\",
            \"projectId\": \"${PROJECT_ID}\",
            \"description\": \"AyuGram-based Telegram Engine for video streaming\"
        }")
    
    APP_ID=$(echo "$CREATE_RESPONSE" | jq -r '.applicationId')
    
    if [ -z "$APP_ID" ] || [ "$APP_ID" = "null" ]; then
        echo -e "${RED}ERROR: Failed to create application${NC}"
        echo "$CREATE_RESPONSE"
        exit 1
    fi
    
    echo -e "${GREEN}Created application: ${APP_NAME} (${APP_ID})${NC}"
else
    echo -e "${GREEN}Application already exists: ${APP_NAME} (${APP_ID})${NC}"
fi

echo -e "${YELLOW}Step 3: Configuring build settings...${NC}"

# Update application with Dockerfile settings
UPDATE_RESPONSE=$(curl -s -X PUT "${DOKPLOY_URL}/api/application.update" \
    -H "x-api-key: ${DOKPLOY_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "{
        \"applicationId\": \"${APP_ID}\",
        \"dockerfile\": \"tg-engine/Dockerfile\",
        \"sourceType\": \"git\",
        \"buildType\": \"dockerfile\"
    }")

echo -e "${YELLOW}Step 4: Setting environment variables...${NC}"

# Set build args (API credentials)
ENV_RESPONSE=$(curl -s -X POST "${DOKPLOY_URL}/api/application.saveEnvironment" \
    -H "x-api-key: ${DOKPLOY_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "{
        \"applicationId\": \"${APP_ID}\",
        \"environment\": \"TDESKTOP_API_ID=37831214\nTDESKTOP_API_HASH=1a10843db60c599ce2ec67bc6a55f1c2\"
    }")

echo -e "${YELLOW}Step 5: Triggering deployment...${NC}"

# Deploy
DEPLOY_RESPONSE=$(curl -s -X POST "${DOKPLOY_URL}/api/application.deploy" \
    -H "x-api-key: ${DOKPLOY_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "{
        \"applicationId\": \"${APP_ID}\"
    }")

echo -e "${GREEN}=========================================="
echo "Deployment triggered!"
echo "==========================================${NC}"
echo ""
echo "Application ID: ${APP_ID}"
echo ""
echo "Monitor progress in Dokploy UI:"
echo "${DOKPLOY_URL}/project/${PROJECT_ID}/application/${APP_ID}"
echo ""
echo -e "${YELLOW}Note: Build may take 30-60 minutes${NC}"
