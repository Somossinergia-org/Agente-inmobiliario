"""Interfaz CLI interactiva del Agente Inmobiliario."""

from __future__ import annotations

import sys
from datetime import datetime

from rich.console import Console
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.panel import Panel
from rich.text import Text

from src.agent.orchestrator import RealEstateAgent
from src.search.engine import SearchFilters
from src.models.client import ClientInterest
from src.utils.formatting import (
    format_property_table,
    format_client_table,
    format_dashboard_panel,
    format_property_detail_panel,
    format_estimation_panel,
    format_comparative_panel,
)

console = Console()


def show_banner():
    banner = Text()
    banner.append("AGENTE INMOBILIARIO", style="bold blue")
    banner.append("\nSistema inteligente de gestion inmobiliaria con CRM completo", style="dim")
    console.print(Panel(banner, border_style="blue"))


def show_menu():
    menu = """
[bold cyan]MENU PRINCIPAL[/bold cyan]

[bold]BUSQUEDA[/bold]
  [cyan]1[/cyan]  Busqueda rapida (texto libre)
  [cyan]2[/cyan]  Busqueda avanzada con filtros
  [cyan]3[/cyan]  Buscar residencial
  [cyan]4[/cyan]  Buscar comercial
  [cyan]5[/cyan]  Buscar terrenos
  [cyan]6[/cyan]  Buscar fincas rusticas
  [cyan]7[/cyan]  Buscar garajes/trasteros
  [cyan]8[/cyan]  Ver detalle de propiedad

[bold]CRM[/bold]
  [cyan]10[/cyan] Ver dashboard
  [cyan]11[/cyan] Listar clientes
  [cyan]12[/cyan] Ver ficha de cliente
  [cyan]13[/cyan] Crear nuevo cliente
  [cyan]14[/cyan] Buscar propiedades para cliente
  [cyan]15[/cyan] Programar visita
  [cyan]16[/cyan] Agregar favorito
  [cyan]17[/cyan] Ver favoritos de cliente

[bold]VALORACION[/bold]
  [cyan]20[/cyan] Estimar precio de propiedad
  [cyan]21[/cyan] Comparativa de mercado
  [cyan]22[/cyan] Estadisticas por zona

  [cyan]0[/cyan]  Salir
"""
    console.print(menu)


def run_cli():
    agent = RealEstateAgent()
    show_banner()

    while True:
        show_menu()
        choice = Prompt.ask("[bold]Selecciona opcion[/bold]", default="0")

        try:
            if choice == "0":
                console.print("[bold blue]Hasta pronto![/bold blue]")
                break

            elif choice == "1":
                query = Prompt.ask("Buscar")
                results = agent.quick_search(query)
                if results:
                    console.print(format_property_table(results, f"Resultados para '{query}'"))
                else:
                    console.print("[yellow]No se encontraron resultados.[/yellow]")

            elif choice == "2":
                console.print("[bold]Busqueda avanzada[/bold]")
                filters = SearchFilters()
                city = Prompt.ask("Ciudad (Enter para todas)", default="")
                if city:
                    filters.cities = [city]
                ptype = Prompt.ask("Tipo (piso/casa/chalet/oficina/terreno_urbano/garaje/etc, Enter para todos)", default="")
                if ptype:
                    filters.property_types = [ptype]
                min_p = Prompt.ask("Precio minimo", default="0")
                filters.min_price = float(min_p)
                max_p = Prompt.ask("Precio maximo (0=sin limite)", default="0")
                if float(max_p) > 0:
                    filters.max_price = float(max_p)
                rental = Prompt.ask("Solo alquiler? (s/n)", default="n")
                if rental.lower() == "s":
                    filters.is_rental = True
                elif rental.lower() == "n":
                    filters.is_rental = False

                results = agent.search_properties(filters)
                if results:
                    console.print(format_property_table(results, "Resultados busqueda avanzada"))
                else:
                    console.print("[yellow]No se encontraron resultados.[/yellow]")

            elif choice == "3":
                city = Prompt.ask("Ciudad (Enter para todas)", default="")
                beds = IntPrompt.ask("Habitaciones minimas", default=0)
                max_p = Prompt.ask("Precio maximo (0=sin limite)", default="0")
                mp = float(max_p) if float(max_p) > 0 else float("inf")
                rental = Confirm.ask("Solo alquiler?", default=False)
                results = agent.search.search_residential(city, beds, mp, rental)
                formatted = [agent._format_property_summary(p) for p in results]
                if formatted:
                    console.print(format_property_table(formatted, "Residencial"))
                else:
                    console.print("[yellow]No se encontraron resultados.[/yellow]")

            elif choice == "4":
                city = Prompt.ask("Ciudad (Enter para todas)", default="")
                results = agent.search.search_commercial(city)
                formatted = [agent._format_property_summary(p) for p in results]
                if formatted:
                    console.print(format_property_table(formatted, "Comercial"))
                else:
                    console.print("[yellow]No se encontraron resultados.[/yellow]")

            elif choice == "5":
                province = Prompt.ask("Provincia (Enter para todas)", default="")
                results = agent.search.search_land(province)
                formatted = [agent._format_property_summary(p) for p in results]
                if formatted:
                    console.print(format_property_table(formatted, "Terrenos"))
                else:
                    console.print("[yellow]No se encontraron resultados.[/yellow]")

            elif choice == "6":
                results = agent.search.search_rural()
                formatted = [agent._format_property_summary(p) for p in results]
                if formatted:
                    console.print(format_property_table(formatted, "Fincas Rusticas"))
                else:
                    console.print("[yellow]No se encontraron resultados.[/yellow]")

            elif choice == "7":
                city = Prompt.ask("Ciudad (Enter para todas)", default="")
                results = agent.search.search_garages(city)
                formatted = [agent._format_property_summary(p) for p in results]
                if formatted:
                    console.print(format_property_table(formatted, "Garajes y Trasteros"))
                else:
                    console.print("[yellow]No se encontraron resultados.[/yellow]")

            elif choice == "8":
                prop_id = Prompt.ask("ID de propiedad")
                detail = agent.get_property_detail(prop_id)
                if detail:
                    console.print(format_property_detail_panel(detail))
                else:
                    console.print("[red]Propiedad no encontrada.[/red]")

            elif choice == "10":
                dashboard = agent.get_dashboard()
                console.print(format_dashboard_panel(dashboard))

            elif choice == "11":
                clients = agent.list_clients()
                if clients:
                    console.print(format_client_table(clients))
                else:
                    console.print("[yellow]No hay clientes registrados.[/yellow]")

            elif choice == "12":
                client_id = Prompt.ask("ID de cliente")
                info = agent.get_client_info(client_id)
                if info:
                    console.print(Panel(str(info), title=f"Cliente {info['name']}", border_style="magenta"))
                else:
                    console.print("[red]Cliente no encontrado.[/red]")

            elif choice == "13":
                name = Prompt.ask("Nombre completo")
                email = Prompt.ask("Email")
                phone = Prompt.ask("Telefono")
                types = Prompt.ask("Tipos de interes (separados por coma)", default="")
                min_p = Prompt.ask("Presupuesto minimo", default="0")
                max_p = Prompt.ask("Presupuesto maximo", default="0")
                cities = Prompt.ask("Ciudades preferidas (separadas por coma)", default="")
                rental = Confirm.ask("Busca alquiler?", default=False)

                interest = ClientInterest(
                    property_types=[t.strip() for t in types.split(",") if t.strip()],
                    min_price=float(min_p),
                    max_price=float(max_p) if float(max_p) > 0 else float("inf"),
                    preferred_cities=[c.strip() for c in cities.split(",") if c.strip()],
                    is_rental=rental,
                )
                client = agent.create_client(name, email, phone, interest)
                console.print(f"[green]Cliente creado: {client.id} - {client.name}[/green]")

            elif choice == "14":
                client_id = Prompt.ask("ID de cliente")
                results = agent.find_properties_for_client(client_id)
                if results:
                    console.print(format_property_table(results, f"Propiedades para {client_id}"))
                else:
                    console.print("[yellow]No se encontraron propiedades que coincidan.[/yellow]")

            elif choice == "15":
                client_id = Prompt.ask("ID de cliente")
                prop_id = Prompt.ask("ID de propiedad")
                date_str = Prompt.ask("Fecha (DD/MM/YYYY HH:MM)", default=datetime.now().strftime("%d/%m/%Y %H:%M"))
                notes = Prompt.ask("Notas", default="")
                visit_date = datetime.strptime(date_str, "%d/%m/%Y %H:%M")
                visit = agent.schedule_visit(client_id, prop_id, visit_date, notes)
                if visit:
                    console.print(f"[green]Visita programada: {visit.id}[/green]")
                else:
                    console.print("[red]No se pudo programar la visita. Verifica los IDs.[/red]")

            elif choice == "16":
                client_id = Prompt.ask("ID de cliente")
                prop_id = Prompt.ask("ID de propiedad")
                notes = Prompt.ask("Notas", default="")
                fav = agent.add_favorite(client_id, prop_id, notes)
                if fav:
                    console.print("[green]Favorito agregado.[/green]")
                else:
                    console.print("[red]No se pudo agregar. Verifica los IDs o si ya existe.[/red]")

            elif choice == "17":
                client_id = Prompt.ask("ID de cliente")
                favs = agent.get_favorites(client_id)
                if favs:
                    for f in favs:
                        console.print(f"  [{f['property_id']}] {f['title']} - {f['price']:,.0f}EUR ({f['city']})")
                else:
                    console.print("[yellow]Sin favoritos.[/yellow]")

            elif choice == "20":
                city = Prompt.ask("Ciudad")
                ptype = Prompt.ask("Tipo de propiedad (piso/casa/chalet/etc)")
                area = float(Prompt.ask("Superficie (m2)"))
                beds = IntPrompt.ask("Habitaciones", default=0)
                estimation = agent.estimate_price(city, ptype, area, beds)
                console.print(format_estimation_panel(estimation))

            elif choice == "21":
                prop_id = Prompt.ask("ID de propiedad")
                comparative = agent.get_comparative(prop_id)
                if comparative:
                    console.print(format_comparative_panel(comparative))
                else:
                    console.print("[red]Propiedad no encontrada.[/red]")

            elif choice == "22":
                city = Prompt.ask("Ciudad")
                stats = agent.get_zone_stats(city)
                console.print(Panel(str(stats), title=f"Estadisticas: {city}", border_style="yellow"))

            else:
                console.print("[red]Opcion no valida.[/red]")

        except KeyboardInterrupt:
            console.print("\n[bold blue]Hasta pronto![/bold blue]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


def main():
    run_cli()


if __name__ == "__main__":
    main()
