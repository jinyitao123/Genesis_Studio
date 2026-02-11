from __future__ import annotations

from pathlib import Path


def test_domain_services_proto_contains_required_services():
    proto_path = Path("proto/genesis_domain_services.proto")
    content = proto_path.read_text(encoding="utf-8")
    required = {
        "service OntologyService",
        "service ObjectService",
        "service LinkService",
        "service TimeTravelService",
        "service SearchService",
        "service AuthService",
        "service NotificationService",
    }
    for item in required:
        assert item in content


def test_backend_service_interface_files_exist():
    expected = [
        "backend/services/ontology_service.py",
        "backend/services/object_service.py",
        "backend/services/link_service.py",
        "backend/services/time_travel_service.py",
        "backend/services/search_service.py",
        "backend/services/auth_service.py",
        "backend/services/notification_service.py",
    ]
    for file_path in expected:
        assert Path(file_path).exists(), file_path
