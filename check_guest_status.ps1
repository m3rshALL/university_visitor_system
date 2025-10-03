# Script to check guest registration status in HikCentral
param(
    [int]$VisitId
)

Write-Host "`n=== GUEST REGISTRATION STATUS ===" -ForegroundColor Cyan

# Check HikAccessTask records
Write-Host "`n1. HikAccessTask records:" -ForegroundColor Yellow
if ($VisitId) {
    docker-compose exec -T db psql -U postgres -d visitor_system_db -c "SELECT id, kind, status, error_message, created_at, updated_at FROM hikvision_integration_hikaccesstask WHERE visit_id = $VisitId ORDER BY id;"
} else {
    docker-compose exec -T db psql -U postgres -d visitor_system_db -c "SELECT id, kind, status, error_message, visit_id, created_at FROM hikvision_integration_hikaccesstask ORDER BY id DESC LIMIT 10;"
}

# Check Visit with HikCentral person ID
Write-Host "`n2. Recent visits with HikCentral person ID:" -ForegroundColor Yellow
if ($VisitId) {
    docker-compose exec -T db psql -U postgres -d visitor_system_db -c "SELECT v.id, v.hikcentral_person_id, g.full_name, v.status FROM visitors_visit v LEFT JOIN visitors_guest g ON v.guest_id = g.id WHERE v.id = $VisitId;"
} else {
    docker-compose exec -T db psql -U postgres -d visitor_system_db -c "SELECT v.id, v.hikcentral_person_id, g.full_name, v.status FROM visitors_visit v LEFT JOIN visitors_guest g ON v.guest_id = g.id ORDER BY v.id DESC LIMIT 5;"
}

# Check HikPersonBinding
Write-Host "`n3. HikPersonBinding records:" -ForegroundColor Yellow
docker-compose exec -T db psql -U postgres -d visitor_system_db -c "SELECT id, guest_id, hikcentral_person_id, created_at FROM hikvision_integration_hikpersonbinding ORDER BY id DESC LIMIT 5;"

Write-Host "`n=================================`n" -ForegroundColor Cyan
