"""Utilidades de formato para la interfaz CLI."""

from __future__ import annotations

from rich.table import Table
from rich.panel import Panel
from rich.text import Text


def format_property_table(properties: list[dict], title: str = "Propiedades") -> Table:
    table = Table(title=title, show_lines=True)
    table.add_column("ID", style="cyan", width=10)
    table.add_column("Titulo", style="white", width=40)
    table.add_column("Tipo", style="magenta", width=15)
    table.add_column("Precio", style="green", justify="right", width=15)
    table.add_column("Ciudad", style="yellow", width=15)
    table.add_column("Superficie", justify="right", width=10)
    table.add_column("Hab.", justify="center", width=5)

    for p in properties:
        table.add_row(
            p.get("id", ""),
            p.get("title", "")[:38],
            p.get("type", ""),
            p.get("price", ""),
            p.get("city", ""),
            p.get("area", ""),
            str(p.get("bedrooms", "-")),
        )
    return table


def format_client_table(clients: list[dict], title: str = "Clientes") -> Table:
    table = Table(title=title, show_lines=True)
    table.add_column("ID", style="cyan", width=12)
    table.add_column("Nombre", style="white", width=30)
    table.add_column("Estado", style="magenta", width=12)
    table.add_column("Busca", style="yellow", width=25)
    table.add_column("Presupuesto", style="green", width=20)
    table.add_column("Visitas", justify="center", width=8)

    for c in clients:
        table.add_row(
            c.get("id", ""),
            c.get("name", ""),
            c.get("status", ""),
            ", ".join(c.get("interest_types", []))[:23],
            c.get("budget", ""),
            str(c.get("visits", 0)),
        )
    return table


def format_dashboard_panel(data: dict) -> Panel:
    text = Text()
    text.append("PROPIEDADES\n", style="bold underline")
    text.append(f"  Total: {data['total_properties']}\n")
    text.append(f"  Disponibles: {data['available']}\n", style="green")
    text.append(f"  Reservadas: {data['reserved']}\n", style="yellow")
    text.append(f"  Vendidas: {data['sold']}\n", style="red")
    text.append(f"  En venta: {data['for_sale']}  |  En alquiler: {data['for_rent']}\n")
    if data['avg_price_sale']:
        text.append(f"  Precio medio (venta): {data['avg_price_sale']:,.0f}EUR\n")
    text.append("\n")
    text.append("CLIENTES\n", style="bold underline")
    text.append(f"  Total: {data['total_clients']}\n")
    text.append(f"  Activos: {data['active_clients']}\n", style="green")
    text.append("\n")
    text.append("POR TIPO\n", style="bold underline")
    for t, count in sorted(data["by_type"].items(), key=lambda x: x[1], reverse=True):
        text.append(f"  {t}: {count}\n")
    text.append("\n")
    text.append("POR CIUDAD (top 10)\n", style="bold underline")
    for city, count in list(data["by_city"].items())[:10]:
        text.append(f"  {city}: {count}\n")

    return Panel(text, title="Dashboard Inmobiliario", border_style="blue")


def format_property_detail_panel(detail: dict) -> Panel:
    text = Text()
    text.append(f"{detail.get('title', '')}\n", style="bold")
    text.append(f"ID: {detail.get('id', '')}\n", style="dim")
    text.append(f"Tipo: {detail.get('type', '')}\n")
    text.append(f"Estado: {detail.get('status', '')}\n")
    text.append("\n")
    text.append(f"Precio: {detail.get('price_formatted', '')}\n", style="bold green")
    text.append(f"Precio/m2: {detail.get('price_per_m2_formatted', '')}\n")
    text.append(f"Superficie: {detail.get('area_m2', '')}m2\n")
    text.append(f"Ubicacion: {detail.get('location', '')}, {detail.get('city', '')} ({detail.get('province', '')})\n")
    text.append("\n")
    text.append(f"{detail.get('description', '')}\n")
    text.append("\n")

    if detail.get("bedrooms") is not None:
        text.append("CARACTERISTICAS\n", style="bold underline")
        text.append(f"  Habitaciones: {detail.get('bedrooms', '-')}\n")
        text.append(f"  Banos: {detail.get('bathrooms', '-')}\n")
        if detail.get("floor") is not None:
            text.append(f"  Planta: {detail['floor']}\n")
        for feat in ["has_elevator", "has_terrace", "has_garage", "has_pool", "has_garden"]:
            if detail.get(feat):
                label = feat.replace("has_", "").replace("_", " ").title()
                text.append(f"  {label}: Si\n", style="green")
        if detail.get("orientation"):
            text.append(f"  Orientacion: {detail['orientation']}\n")
        if detail.get("community_fees"):
            text.append(f"  Comunidad: {detail['community_fees']}EUR/mes\n")

    if detail.get("energy_rating"):
        text.append(f"\nEficiencia energetica: {detail['energy_rating']}\n")

    if detail.get("features"):
        text.append("\nExtras: ", style="bold")
        text.append(", ".join(detail["features"]) + "\n")

    return Panel(text, title="Detalle de Propiedad", border_style="green")


def format_estimation_panel(estimation) -> Panel:
    text = Text()
    text.append("ESTIMACION DE PRECIO\n", style="bold underline")
    text.append(f"  Precio estimado: {estimation.estimated_price:,.0f}EUR\n", style="bold green")
    text.append(f"  Precio/m2 medio: {estimation.price_per_m2:,.0f}EUR/m2\n")
    text.append(f"  Rango: {estimation.min_price:,.0f}EUR - {estimation.max_price:,.0f}EUR\n")
    text.append(f"  Precio medio comparable: {estimation.avg_price:,.0f}EUR\n")
    text.append(f"  Comparables analizados: {estimation.comparable_count}\n")
    text.append(f"  Confianza: {estimation.confidence}\n")

    if estimation.comparables:
        text.append("\nCOMPARABLES\n", style="bold underline")
        for c in estimation.comparables[:5]:
            text.append(f"  - {c['title']} | {c['price']:,.0f}EUR | {c['price_per_m2']:,.0f}EUR/m2\n")

    return Panel(text, title="Valoracion de Mercado", border_style="yellow")


def format_comparative_panel(comparative) -> Panel:
    text = Text()
    text.append("INFORME COMPARATIVO\n\n", style="bold underline")
    text.append(f"{comparative.market_summary}\n\n")
    text.append(f"  Precio/m2 de la propiedad: {comparative.property.price_per_m2:,.0f}EUR/m2\n")
    text.append(f"  Media de la zona: {comparative.avg_price_m2_zone:,.0f}EUR/m2\n")
    text.append(f"  Diferencia: {comparative.price_difference_pct:+.1f}%\n")
    text.append(f"  Posicion: {comparative.price_position}\n")

    if comparative.similar_properties:
        text.append("\nPROPIEDADES SIMILARES\n", style="bold underline")
        for s in comparative.similar_properties[:5]:
            text.append(f"  - {s['title']} | {s['price']:,.0f}EUR | {s['difference']}\n")

    return Panel(text, title="Comparativa de Mercado", border_style="cyan")
