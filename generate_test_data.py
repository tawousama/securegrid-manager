#!/usr/bin/env python3
"""
Génération de données réalistes — Projet EPR2 Penly (PostgreSQL optimisé)

Crée un jeu de données complet et cohérent pour tester la plateforme :
- Utilisateurs (admin, ingénieurs, techniciens)
- Types de câbles (normes IEC)
- Chemins de câbles (cable trays)
- Câbles installés avec routage
- Borniers et bornes
- Raccordements électriques
- Schémas électriques
- Équipements réseau (serveurs, automates, switches)
- Vulnérabilités CVE simulées

Optimisations PostgreSQL :
- Transactions atomiques (ACID)
- Réinitialisation des séquences après --clear
- Gestion des contraintes UNIQUE
- bulk_create pour performance

Usage:
    python generate_test_data.py [--small|--medium|--large]
    
    --small  : 10 câbles, 5 équipements  (test rapide)
    --medium : 50 câbles, 20 équipements (par défaut)
    --large  : 200 câbles, 50 équipements (test complet)
"""

import os
import sys
import django
from pathlib import Path
from datetime import datetime, timedelta
import random

# Setup Django
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction, connection
from apps.electrical.cable_routing.models import CableType, CablePathway, Cable
from apps.electrical.connections.models import TerminalBlock, Terminal, Connection, ConnectionPoint
from apps.electrical.schematics.models import Schematic, SchematicElement
from apps.devices.models import Device, DevicePort, DeviceVulnerability, DeviceScan

User = get_user_model()

# Couleurs
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'

# ═══════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════

DATASET_SIZES = {
    'small': {
        'cables': 10,
        'devices': 5,
        'connections': 5,
        'pathways': 8,
    },
    'medium': {
        'cables': 50,
        'devices': 20,
        'connections': 30,
        'pathways': 15,
    },
    'large': {
        'cables': 200,
        'devices': 50,
        'connections': 100,
        'pathways': 30,
    }
}

# ═══════════════════════════════════════════════════════════
# DONNÉES RÉALISTES EPR2 PENLY
# ═══════════════════════════════════════════════════════════

CABLE_TYPES_EPR = [
    {
        'reference': 'U1000R2V-3G1.5',
        'name': 'Câble U1000R2V 3G1.5mm² cuivre',
        'section_mm2': 1.5,
        'conductor_count': 3,
        'conductor_material': 'copper',
        'voltage_max': 1000,
        'standard': 'IEC',
    },
    {
        'reference': 'U1000R2V-3G2.5',
        'name': 'Câble U1000R2V 3G2.5mm² cuivre',
        'section_mm2': 2.5,
        'conductor_count': 3,
        'conductor_material': 'copper',
        'voltage_max': 1000,
        'standard': 'IEC',
    },
    {
        'reference': 'U1000R2V-3G4',
        'name': 'Câble U1000R2V 3G4mm² cuivre',
        'section_mm2': 4.0,
        'conductor_count': 3,
        'conductor_material': 'copper',
        'voltage_max': 1000,
        'standard': 'IEC',
    },
    {
        'reference': 'U1000R2V-3G6',
        'name': 'Câble U1000R2V 3G6mm² cuivre',
        'section_mm2': 6.0,
        'conductor_count': 3,
        'conductor_material': 'copper',
        'voltage_max': 1000,
        'standard': 'IEC',
    },
    {
        'reference': 'U1000R2V-3G10',
        'name': 'Câble U1000R2V 3G10mm² cuivre',
        'section_mm2': 10.0,
        'conductor_count': 3,
        'conductor_material': 'copper',
        'voltage_max': 1000,
        'standard': 'IEC',
    },
    {
        'reference': 'U1000R2V-5G6',
        'name': 'Câble U1000R2V 5G6mm² cuivre (3P+N+PE)',
        'section_mm2': 6.0,
        'conductor_count': 5,
        'conductor_material': 'copper',
        'voltage_max': 1000,
        'standard': 'IEC',
    },
    {
        'reference': 'U1000R2V-5G16',
        'name': 'Câble U1000R2V 5G16mm² cuivre',
        'section_mm2': 16.0,
        'conductor_count': 5,
        'conductor_material': 'copper',
        'voltage_max': 1000,
        'standard': 'IEC',
    },
    {
        'reference': 'U1000R2V-5G25',
        'name': 'Câble U1000R2V 5G25mm² cuivre',
        'section_mm2': 25.0,
        'conductor_count': 5,
        'conductor_material': 'copper',
        'voltage_max': 1000,
        'standard': 'IEC',
    },
]

ZONES_EPR = [
    'BEP-N4',  # Bâtiment Électrique Principal
    'BK-N4',   # Bâtiment des auxiliaires nucléaires
    'BR-DDG',  # Bâtiment Réacteur - Diesel de Secours
    'BAN',     # Bâtiment Auxiliaire Nucléaire
    'TGBT-A',  # Tableau Général Basse Tension A
    'TGBT-B',  # Tableau Général Basse Tension B
    'TD-01',   # Tableau Divisionnaire 01
    'TD-02',   # Tableau Divisionnaire 02
]

EQUIPMENT_TYPES = [
    ('MOT', 'Moteur'),
    ('PMP', 'Pompe'),
    ('VNT', 'Ventilateur'),
    ('ECV', 'Éclairage'),
    ('PRS', 'Prise de courant'),
    ('SRV', 'Serveur'),
    ('SWI', 'Switch réseau'),
    ('PLC', 'Automate'),
    ('CAM', 'Caméra IP'),
]

# ═══════════════════════════════════════════════════════════
# HELPERS POSTGRESQL
# ═══════════════════════════════════════════════════════════

def reset_sequences():
    """Réinitialise les séquences PostgreSQL après suppression des données."""
    if connection.vendor == 'postgresql':
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT sequence_name 
                FROM information_schema.sequences 
                WHERE sequence_schema = 'public'
            """)
            sequences = cursor.fetchall()
            for (seq_name,) in sequences:
                try:
                    cursor.execute(f"ALTER SEQUENCE {seq_name} RESTART WITH 1")
                except Exception:
                    pass  # Ignorer les erreurs (séquences qui n'existent plus)
        print(f"{GREEN}✓ Séquences PostgreSQL réinitialisées{RESET}")

def get_db_info():
    """Affiche les informations sur la base de données."""
    db_settings = connection.settings_dict
    vendor = connection.vendor
    
    if vendor == 'postgresql':
        db_name = db_settings.get('NAME')
        db_user = db_settings.get('USER')
        db_host = db_settings.get('HOST', 'localhost')
        
        print(f"{BLUE}Base de données : PostgreSQL{RESET}")
        print(f"  • Database : {db_name}")
        print(f"  • User     : {db_user}")
        print(f"  • Host     : {db_host}")
    elif vendor == 'sqlite':
        print(f"{YELLOW}Base de données : SQLite (pour tests uniquement){RESET}")
    else:
        print(f"Base de données : {vendor}")
    print()

# ═══════════════════════════════════════════════════════════
# GÉNÉRATEURS
# ═══════════════════════════════════════════════════════════

class DataGenerator:
    def __init__(self, size='medium'):
        self.size = size
        self.config = DATASET_SIZES[size]
        self.admin_user = None
        self.cable_types = {}
        self.pathways = []
        self.cables = []
        self.terminal_blocks = []
        self.devices = []
        
        print(f"\n{BLUE}═══ Génération de données EPR2 Penly — Jeu {size.upper()} ═══{RESET}\n")
        get_db_info()
    
    def generate_all(self):
        """Génère toutes les données."""
        try:
            self.create_users()
            self.create_cable_types()
            self.create_pathways()
            self.create_cables()
            self.create_terminal_blocks()
            self.create_connections()
            self.create_schematics()
            self.create_devices()
            self.create_scans()
            self.print_summary()
        except Exception as e:
            print(f"\n{RED}❌ ERREUR : {e}{RESET}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    @transaction.atomic
    def create_users(self):
        """Crée les utilisateurs."""
        print(f"{YELLOW}Création des utilisateurs...{RESET}")
        
        # Admin
        self.admin_user, created = User.objects.get_or_create(
            email='admin@energy.fr',
            defaults={
                'first_name': 'Jean',
                'last_name': 'Martin',
                'role': 'admin',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            self.admin_user.set_password('Admin123!')
            self.admin_user.save()
        else:
            # Mettre à jour si existe déjà
            self.admin_user.is_staff = True
            self.admin_user.is_superuser = True
            self.admin_user.set_password('Admin123!')
            self.admin_user.save()
        
        # Ingénieurs
        engineers = [
            ('pierre.dupont@energy.fr', 'Pierre', 'Dupont'),
            ('marie.bernard@energy.fr', 'Marie', 'Bernard'),
            ('luc.moreau@energy.fr', 'Luc', 'Moreau'),
        ]
        for email, first, last in engineers:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'role': 'engineer',
                }
            )
            if created:
                user.set_password('Engineer123!')
                user.save()
        
        # Techniciens
        techs = [
            ('thomas.petit@energy.fr', 'Thomas', 'Petit'),
            ('sophie.roux@energy.fr', 'Sophie', 'Roux'),
        ]
        for email, first, last in techs:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'role': 'technician',
                }
            )
            if created:
                user.set_password('Tech123!')
                user.save()
        
        print(f"{GREEN}✓{RESET} {User.objects.count()} utilisateurs\n")
    
    @transaction.atomic
    def create_cable_types(self):
        """Crée les types de câbles."""
        print(f"{YELLOW}Création des types de câbles...{RESET}")
        
        for ct_data in CABLE_TYPES_EPR:
            ct, created = CableType.objects.get_or_create(
                reference=ct_data['reference'],
                defaults={**ct_data, 'created_by': self.admin_user}
            )
            self.cable_types[ct_data['reference']] = ct
        
        print(f"{GREEN}✓{RESET} {len(self.cable_types)} types de câbles\n")
    
    @transaction.atomic
    def create_pathways(self):
        """Crée les chemins de câbles."""
        print(f"{YELLOW}Création des chemins de câbles...{RESET}")
        
        # Chemins horizontaux dans chaque zone
        x_positions = [0, 50, 100, 150, 200]
        y_positions = [0, 30, 60]
        
        for i, zone in enumerate(ZONES_EPR[:self.config['pathways']]):
            x = x_positions[i % len(x_positions)]
            y = y_positions[i % len(y_positions)]
            
            pathway, created = CablePathway.objects.get_or_create(
                reference=f'PATHWAY-{zone}',
                defaults={
                    'name': f'Chemin de câbles {zone}',
                    'pathway_type': 'cable_tray',
                    'start_x': x,
                    'start_y': y,
                    'start_z': 3.0,
                    'end_x': x + 40,
                    'end_y': y,
                    'end_z': 3.0,
                    'width_mm': 300,
                    'height_mm': 100,
                    'max_fill_ratio': 0.40,
                    'created_by': self.admin_user
                }
            )
            self.pathways.append(pathway)
            
            # Connexions entre pathways adjacents
            if len(self.pathways) > 1:
                pathway.connected_pathways.add(self.pathways[-2])
        
        print(f"{GREEN}✓{RESET} {len(self.pathways)} chemins de câbles\n")
    
    @transaction.atomic
    def create_cables(self):
        """Crée les câbles."""
        print(f"{YELLOW}Création des câbles...{RESET}")
        
        for i in range(self.config['cables']):
            zone_origin = random.choice(ZONES_EPR[:4])
            zone_dest = random.choice(ZONES_EPR[4:])
            equip_type, equip_name = random.choice(EQUIPMENT_TYPES)
            
            # Choisir un type de câble selon la puissance
            if equip_type in ['MOT', 'PMP', 'VNT']:
                cable_type_ref = random.choice(['U1000R2V-5G6', 'U1000R2V-5G16', 'U1000R2V-5G25'])
                current = random.randint(16, 63)
            else:
                cable_type_ref = random.choice(['U1000R2V-3G1.5', 'U1000R2V-3G2.5', 'U1000R2V-3G4'])
                current = random.randint(6, 20)
            
            cable, created = Cable.objects.get_or_create(
                reference=f'CAB-EPR-{i+1:04d}',
                defaults={
                    'cable_type': self.cable_types[cable_type_ref],
                    'designed_length_m': random.uniform(15.0, 150.0),
                    'origin_label': zone_origin,
                    'destination_label': f'{zone_dest}-{equip_type}-{i+1:03d}',
                    'design_current_a': current,
                    'operating_voltage': 400,
                    'status': 'installed',
                    'created_by': self.admin_user
                }
            )
            self.cables.append(cable)
        
        print(f"{GREEN}✓{RESET} {len(self.cables)} câbles\n")
    
    @transaction.atomic
    def create_terminal_blocks(self):
        """Crée les borniers et bornes."""
        print(f"{YELLOW}Création des borniers et bornes...{RESET}")
        
        terminal_count = 0
        for zone in ZONES_EPR[4:]:  # TGBT et TD seulement
            block, created = TerminalBlock.objects.get_or_create(
                reference=f'{zone}-X1',
                defaults={
                    'name': f'Bornier principal {zone}',
                    'location': f'Armoire {zone}',
                    'equipment_ref': zone,
                    'voltage_rating': 400,
                    'current_rating': 125,
                    'max_section_mm2': 25.0,
                    'manufacturer': 'Phoenix Contact',
                    'created_by': self.admin_user
                }
            )
            self.terminal_blocks.append(block)
            
            # Créer 24 bornes par bornier (seulement si créé)
            if created:
                terminals_to_create = []
                for i in range(1, 25):
                    terminals_to_create.append(Terminal(
                        block=block,
                        label=f'X1:{i}',
                        position=i,
                        terminal_type='screw',
                        max_section_mm2=16.0,
                        voltage_rating=400,
                        current_rating=32,
                        recommended_torque_nm=2.5
                    ))
                
                # Bulk create pour performance
                Terminal.objects.bulk_create(terminals_to_create)
                terminal_count += len(terminals_to_create)
            else:
                terminal_count += Terminal.objects.filter(block=block).count()
        
        print(f"{GREEN}✓{RESET} {len(self.terminal_blocks)} borniers, {terminal_count} bornes\n")
    
    @transaction.atomic
    def create_connections(self):
        """Crée les raccordements."""
        print(f"{YELLOW}Création des raccordements...{RESET}")
        
        terminals = list(Terminal.objects.filter(is_occupied=False)[:self.config['connections'] * 2])
        connection_count = 0
        
        for i in range(0, min(len(terminals) - 1, self.config['connections'] * 2), 2):
            if i >= len(self.cables):
                break
                
            cable = self.cables[i % len(self.cables)]
            terminal_origin = terminals[i]
            terminal_dest = terminals[i + 1]
            
            conn, created = Connection.objects.get_or_create(
                reference=f'CONN-EPR-{connection_count+1:04d}',
                defaults={
                    'name': f'Raccordement {cable.reference}',
                    'cable': cable,
                    'terminal_origin': terminal_origin,
                    'terminal_dest': terminal_dest,
                    'connection_type': 'terminal',
                    'status': 'completed',
                    'created_by': self.admin_user
                }
            )
            
            if created:
                # Points de raccordement (L1, N, PE)
                conductors = [
                    ('L1', 'brown'),
                    ('N', 'blue'),
                    ('PE', 'yellow_green'),
                ]
                points_to_create = []
                for conductor, color in conductors:
                    points_to_create.append(ConnectionPoint(
                        connection=conn,
                        terminal=terminal_origin if conductor in ['L1', 'N'] else terminal_dest,
                        conductor=conductor,
                        wire_color=color,
                        tightening_torque_nm=2.5,
                        has_ferrule=True,
                        is_verified=True
                    ))
                
                ConnectionPoint.objects.bulk_create(points_to_create)
                
                terminal_origin.is_occupied = True
                terminal_origin.save()
                terminal_dest.is_occupied = True
                terminal_dest.save()
            
            connection_count += 1
        
        print(f"{GREEN}✓{RESET} {connection_count} raccordements\n")
    
    @transaction.atomic
    def create_schematics(self):
        """Crée les schémas électriques."""
        print(f"{YELLOW}Création des schémas électriques...{RESET}")
        
        schematic, created = Schematic.objects.get_or_create(
            reference='SCH-EPR-TGBT-A',
            defaults={
                'title': 'Schéma unifilaire TGBT-A — EPR2 Penly',
                'schematic_type': 'single_line',
                'status': 'approved',
                'version': 'Rev.2',
                'standard': 'IEC',
                'project_ref': 'EPR2-PENLY',
                'zone': 'TGBT-A',
                'created_by': self.admin_user
            }
        )
        
        # Quelques éléments symboliques (seulement si créé)
        if created:
            elements_data = [
                ('Arrivée TGBT', 'bus', 50, 20),
                ('Disjoncteur Q1', 'circuit_breaker', 50, 50),
                ('Départ MOT-001', 'cable', 50, 80),
            ]
            
            elements_to_create = []
            for label, elem_type, x, y in elements_data:
                elements_to_create.append(SchematicElement(
                    schematic=schematic,
                    element_type=elem_type,
                    label=label,
                    x=x,
                    y=y,
                    width=20,
                    height=10
                ))
            
            SchematicElement.objects.bulk_create(elements_to_create)
        
        print(f"{GREEN}✓{RESET} 1 schéma électrique\n")
    
    @transaction.atomic
    def create_devices(self):
        """Crée les équipements réseau."""
        print(f"{YELLOW}Création des équipements réseau...{RESET}")
        
        device_types_map = {
            'server': ['SRV'],
            'switch': ['SWI'],
            'plc': ['PLC'],
            'iot': ['CAM'],
        }
        
        os_choices = {
            'server': ['Ubuntu 22.04 LTS', 'Windows Server 2022', 'RedHat Enterprise Linux 8'],
            'switch': ['Cisco IOS 15.2', 'Juniper Junos 21.4'],
            'plc': ['Siemens TIA Portal V17', 'Schneider Unity Pro'],
            'iot': ['Linux embedded 5.10', 'FreeRTOS'],
        }
        
        for i in range(self.config['devices']):
            device_type = random.choice(list(device_types_map.keys()))
            prefix = random.choice(device_types_map[device_type])
            
            device, created = Device.objects.get_or_create(
                reference=f'DEV-{prefix}-{i+1:03d}',
                defaults={
                    'name': f'{prefix} EPR2 Penly {i+1:03d}',
                    'device_type': device_type,
                    'ip_address': f'10.0.{random.randint(1,10)}.{random.randint(10,250)}',
                    'mac_address': ':'.join([f'{random.randint(0,255):02x}' for _ in range(6)]),
                    'hostname': f'{prefix.lower()}-epr2-{i+1:03d}',
                    'vlan': random.choice([10, 20, 30, 100]),
                    'os': random.choice(os_choices[device_type]),
                    'firmware_version': f'{random.randint(1,5)}.{random.randint(0,9)}.{random.randint(0,20)}',
                    'location': f'{random.choice(ZONES_EPR)}, Rack R{random.randint(1,8)}',
                    'power_cable_ref': f'CAB-EPR-{random.randint(1, len(self.cables)):04d}' if self.cables else '',
                    'criticality': random.choice(['medium', 'high', 'critical']),
                    'is_monitored': True,
                    'last_seen': timezone.now() - timedelta(minutes=random.randint(0, 30)),
                    'created_by': self.admin_user
                }
            )
            self.devices.append(device)
            
            # Ports réseau (seulement si créé)
            if created:
                port_configs = {
                    'server': [(22, 'tcp', 'ssh'), (443, 'tcp', 'https'), (3306, 'tcp', 'mysql')],
                    'switch': [(22, 'tcp', 'ssh'), (23, 'tcp', 'telnet'), (161, 'udp', 'snmp')],
                    'plc': [(102, 'tcp', 's7comm'), (502, 'tcp', 'modbus'), (4840, 'tcp', 'opc-ua')],
                    'iot': [(80, 'tcp', 'http'), (443, 'tcp', 'https'), (554, 'tcp', 'rtsp')],
                }
                
                ports_to_create = []
                for port_num, protocol, service in port_configs.get(device_type, []):
                    ports_to_create.append(DevicePort(
                        device=device,
                        port_number=port_num,
                        protocol=protocol,
                        state='open',
                        service=service,
                        is_authorized=True
                    ))
                
                DevicePort.objects.bulk_create(ports_to_create)
        
        print(f"{GREEN}✓{RESET} {len(self.devices)} équipements réseau\n")
    
    @transaction.atomic
    def create_scans(self):
        """Crée des scans et vulnérabilités."""
        print(f"{YELLOW}Création des scans et vulnérabilités...{RESET}")
        
        vuln_templates = [
            ('CVE-2023-1234', 7.5, 'OpenSSL vulnerability'),
            ('CVE-2023-5678', 9.8, 'Remote Code Execution'),
            ('CVE-2023-9012', 6.5, 'Privilege Escalation'),
        ]
        
        scan_count = 0
        vuln_count = 0
        
        scans_to_create = []
        vulns_to_create = []
        
        for device in self.devices[:self.config['devices'] // 2]:
            # Scan
            scan = DeviceScan(
                device=device,
                scan_type='full',
                started_at=timezone.now() - timedelta(hours=1),
                completed_at=timezone.now() - timedelta(minutes=30),
                result='success',
                ports_found=device.ports.count(),
                open_ports_found=device.ports.filter(state='open').count(),
                vulnerabilities_found=random.randint(0, 2),
                launched_by=self.admin_user
            )
            scans_to_create.append(scan)
            scan_count += 1
            
            # Vulnérabilités aléatoires
            if random.random() < 0.3:  # 30% ont des CVE
                cve_id, score, title = random.choice(vuln_templates)
                print(f'{cve_id}')
                vuln = DeviceVulnerability(
                    device=device,
                    cve_id=f'{cve_id}',
                    cvss_score=score,
                    severity=DeviceVulnerability.severity_from_score(score),
                    title=title,
                    description=f'Vulnerability detected on {device.name}',
                    affected_component=device.os,
                    remediation='Apply security patch',
                    status='open',
                    detected_at=timezone.now() - timedelta(days=random.randint(1, 30))
                )
                vulns_to_create.append(vuln)
                vuln_count += 1
        
        # Bulk create pour performance
        DeviceScan.objects.bulk_create(scans_to_create)
        DeviceVulnerability.objects.bulk_create(vulns_to_create)
        
        print(f"{GREEN}✓{RESET} {scan_count} scans, {vuln_count} vulnérabilités\n")
    
    def print_summary(self):
        """Affiche le résumé."""
        print(f"\n{BLUE}═══════════════════════════════════════════════════════════{RESET}")
        print(f"\n{GREEN}✅ Données générées avec succès !{RESET}\n")
        print(f"👥 Utilisateurs        : {User.objects.count()}")
        print(f"⚡ Types de câbles     : {CableType.objects.count()}")
        print(f"📏 Chemins de câbles   : {CablePathway.objects.count()}")
        print(f"🔌 Câbles              : {Cable.objects.count()}")
        print(f"🔩 Borniers            : {TerminalBlock.objects.count()}")
        print(f"🔗 Bornes              : {Terminal.objects.count()}")
        print(f"🔌 Raccordements       : {Connection.objects.count()}")
        print(f"📐 Schémas             : {Schematic.objects.count()}")
        print(f"🖥️  Équipements        : {Device.objects.count()}")
        print(f"🔍 Scans               : {DeviceScan.objects.count()}")
        print(f"🔴 Vulnérabilités      : {DeviceVulnerability.objects.count()}")
        
        print(f"\n{YELLOW}Identifiants de connexion :{RESET}")
        print(f"  Admin     : admin@energy.fr / Admin123!")
        print(f"  Ingénieur : pierre.dupont@energy.fr / Engineer123!")
        print(f"  Technicien: thomas.petit@energy.fr / Tech123!")
        
        print(f"\n{YELLOW}URLs :{RESET}")
        print(f"  API       : http://localhost:8000/api/v1/")
        print(f"  Admin     : http://localhost:8000/admin/")
        
        print(f"\n{BLUE}═══════════════════════════════════════════════════════════{RESET}\n")

# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Génération de données EPR2 Penly')
    parser.add_argument('--size', choices=['small', 'medium', 'large'], default='medium',
                        help='Taille du jeu de données')
    parser.add_argument('--clear', action='store_true',
                        help='Effacer toutes les données existantes avant génération')
    args = parser.parse_args()
    
    if args.clear:
        print(f"\n{YELLOW}⚠️  Suppression des données existantes...{RESET}")
        
        with transaction.atomic():
            # Supprimer dans l'ordre inverse des dépendances
            DeviceScan.objects.all().delete()
            DeviceVulnerability.objects.all().delete()
            DevicePort.objects.all().delete()
            Device.objects.all().delete()
            SchematicElement.objects.all().delete()
            Schematic.objects.all().delete()
            ConnectionPoint.objects.all().delete()
            Connection.objects.all().delete()
            Terminal.objects.all().delete()
            TerminalBlock.objects.all().delete()
            
            Cable.objects.all().delete()
            CablePathway.objects.all().delete()
            CableType.objects.all().delete()
            User.objects.filter(is_superuser=False, is_staff=False).delete()
        
        print(f"{GREEN}✓ Données effacées{RESET}")
        
        # Réinitialiser les séquences PostgreSQL
        reset_sequences()
        print()
    
    generator = DataGenerator(size=args.size)
    generator.generate_all()

if __name__ == '__main__':
    main()