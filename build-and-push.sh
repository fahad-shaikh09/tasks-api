#!/bin/bash

# Automated Docker Build and Push Script
# Automatically detects latest version and increments by 1

set -e  # Exit on error

echo "=========================================="
echo "Docker Build and Push Script"
echo "=========================================="
echo ""

# Prompt for Docker Hub username
read -p "Enter Docker Hub username: " USERNAME
if [ -z "$USERNAME" ]; then
    echo "❌ Error: Username is required"
    exit 1
fi

# Prompt for repository name
read -p "Enter repository name: " REPO
if [ -z "$REPO" ]; then
    echo "❌ Error: Repository name is required"
    exit 1
fi

echo ""
echo "=========================================="
echo "Repository: ${USERNAME}/${REPO}"
echo "=========================================="
echo ""

# Function to get latest version from Docker Hub
get_latest_version() {
    echo "🔍 Fetching existing tags from Docker Hub..." >&2

    # Get all tags from Docker Hub
    local response=$(curl -s "https://hub.docker.com/v2/repositories/${USERNAME}/${REPO}/tags/?page_size=100")

    # Check if repository exists
    if echo "$response" | grep -q "Object not found"; then
        echo "⚠️  Repository not found on Docker Hub (this might be first push)" >&2
        echo "Starting with version: v1" >&2
        echo 1
        return
    fi

    # Extract version tags (v1, v2, v3, etc.)
    local tags=$(echo "$response" | grep -o '"name":"v[0-9]\+[^"]*"' | cut -d'"' -f4 | grep -E '^v[0-9]+' | sed 's/-neon//g' | sed 's/-local-db//g' | sort -u | sort -V)

    if [ -z "$tags" ]; then
        echo "No existing version tags found." >&2
        echo "Starting with version: v1" >&2
        echo 1
        return
    fi

    # Get the latest version (highest number)
    local latest=$(echo "$tags" | tail -1)
    local version_num=$(echo "$latest" | grep -o '[0-9]\+')

    echo "" >&2
    echo "📋 Latest version found: $latest" >&2
    echo "" >&2

    # Return the latest version number
    echo "$version_num"
}

# Get latest version number and increment
LATEST_VERSION=$(get_latest_version)
NEW_VERSION=$((LATEST_VERSION + 1))
VERSION="v${NEW_VERSION}"

echo "=========================================="
echo "🆕 New version to push: $VERSION"
echo "=========================================="
echo ""

# Confirm with user
read -p "Continue with version ${VERSION}? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "Aborted by user."
    exit 0
fi

echo ""
echo "=========================================="
echo "Starting build process..."
echo "=========================================="

# Build Neon image
echo ""
echo "📦 Building Neon image..."
docker build -f Dockerfile.neon -t ${USERNAME}/${REPO}:${VERSION}-neon .

# Build Local DB image
echo ""
echo "📦 Building Local DB image..."
docker build -f Dockerfile.local -t ${USERNAME}/${REPO}:${VERSION}-local-db .

echo ""
echo "=========================================="
echo "🚀 Pushing images to Docker Hub..."
echo "=========================================="

# Push Neon image
echo ""
echo "📤 Pushing Neon image..."
docker push ${USERNAME}/${REPO}:${VERSION}-neon

# Push Local DB image
echo ""
echo "📤 Pushing Local DB image..."
docker push ${USERNAME}/${REPO}:${VERSION}-local-db

echo ""
echo "=========================================="
echo "✅ Successfully pushed both images!"
echo "=========================================="
echo ""
echo "🎉 Images pushed:"
echo "   • ${USERNAME}/${REPO}:${VERSION}-neon"
echo "   • ${USERNAME}/${REPO}:${VERSION}-local-db"
echo ""
echo "🔗 View on Docker Hub:"
echo "   https://hub.docker.com/r/${USERNAME}/${REPO}/tags"
echo ""
