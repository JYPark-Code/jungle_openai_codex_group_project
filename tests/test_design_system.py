def test_homeschool_design_system_page_renders(client):
    response = client.get("/design-system/homeschool")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Homeschool Design System" in html
    assert "Foundation Tokens" in html
    assert "Today Tasks" in html
