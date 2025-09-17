#!/bin/bash

echo "========================================="
echo "pgAdmin Setup Instructions"
echo "========================================="
echo ""
echo "✅ pgAdmin is running successfully!"
echo ""
echo "📌 Access pgAdmin at:"
echo "   http://localhost:5050"
echo ""
echo "🔑 Login Credentials:"
echo "   Email: admin@4genthub.com"
echo "   Password: AdminPassword2025!"
echo ""
echo "========================================="
echo "After logging in, add a new server with:"
echo "========================================="
echo ""
echo "1. Click 'Add New Server' or right-click 'Servers' → 'Register' → 'Server'"
echo ""
echo "2. General Tab:"
echo "   Name: 4genthub Database"
echo ""
echo "3. Connection Tab:"
echo "   Host: postgres"
echo "   Port: 5432"
echo "   Database: 4genthub_prod"
echo "   Username: 4genthub_user"
echo "   Password: ChangeThisSecurePassword2025!"
echo "   Save password: ✓ (check this box)"
echo ""
echo "4. Click 'Save'"
echo ""
echo "========================================="
echo "Current container status:"
echo "========================================="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(NAME|postgres|pgadmin)"
echo ""
echo "========================================="
echo "Test database connection from Docker:"
echo "========================================="
docker exec 4genthub-postgres psql -U 4genthub_user -d 4genthub_prod -c "SELECT 'Database connection successful!' as status;" 2>/dev/null

# Open browser if available
if command -v xdg-open > /dev/null; then
    echo ""
    echo "Opening browser to http://localhost:5050..."
    xdg-open http://localhost:5050
elif command -v open > /dev/null; then
    echo ""
    echo "Opening browser to http://localhost:5050..."
    open http://localhost:5050
fi