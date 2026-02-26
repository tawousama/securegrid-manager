"""
Moteur de routage de câbles — Calcul automatique du tracé optimal.

Algorithme : BFS (Breadth-First Search) sur un graphe de pathways.

Concept :
    Les chemins de câbles (pathways) forment un graphe.
    Chaque pathway est un nœud, les connexions entre eux sont les arêtes.
    On cherche le chemin le plus court entre l'origine et la destination.

Étapes :
    1. Trouver le pathway le plus proche de l'origine
    2. Trouver le pathway le plus proche de la destination
    3. Appliquer BFS pour trouver le chemin entre ces deux pathways
    4. Construire la liste de waypoints à partir de ce chemin
    5. Calculer la longueur totale

Analogie :
    Imaginez un réseau de routes dans une ville.
    Les pathways sont les routes, les intersections sont les connexions.
    BFS trouve le chemin le plus court (en nombre de routes empruntées).
"""

import math
from collections import deque
from typing import Optional

from ..models import CablePathway, CableRoute, RouteWaypoint


class RoutingEngine:
    """
    Moteur de calcul du tracé d'un câble.

    Usage :
        engine = RoutingEngine()
        result = engine.calculate_route(
            cable=cable,
            origin={'x': 0, 'y': 0, 'z': 3},
            destination={'x': 85, 'y': 50, 'z': 0}
        )
        # result = {
        #   'success': True,
        #   'route': <CableRoute>,
        #   'total_length': 152.3,
        #   'waypoints': [...],
        #   'message': 'Tracé calculé avec succès'
        # }
    """

    def __init__(self):
        # Charger tous les pathways actifs en mémoire une seule fois
        self._pathways = list(
            CablePathway.objects.filter(is_active=True)
            .prefetch_related('connected_pathways')
        )

    # --------------------------------------------------------
    # MÉTHODE PRINCIPALE
    # --------------------------------------------------------

    def calculate_route(self, cable, origin: dict, destination: dict) -> dict:
        """
        Calcule le tracé optimal pour un câble.

        Args:
            cable       : Instance du modèle Cable
            origin      : {'x': float, 'y': float, 'z': float}
            destination : {'x': float, 'y': float, 'z': float}

        Returns:
            dict : {
                'success': bool,
                'route': CableRoute | None,
                'total_length': float,
                'waypoints': list,
                'message': str
            }
        """
        if not self._pathways:
            return {
                'success': False,
                'route': None,
                'total_length': 0,
                'waypoints': [],
                'message': "Aucun chemin de câbles disponible dans la base de données."
            }

        # 1. Trouver les pathways les plus proches des extrémités
        origin_pathway = self._find_nearest_pathway(origin)
        dest_pathway   = self._find_nearest_pathway(destination)

        if not origin_pathway or not dest_pathway:
            return {
                'success': False,
                'route': None,
                'total_length': 0,
                'waypoints': [],
                'message': "Impossible de trouver un chemin de câbles à proximité des extrémités."
            }

        # 2. Cas simple : même pathway pour l'origine et la destination
        if origin_pathway.id == dest_pathway.id:
            pathway_sequence = [origin_pathway]
        else:
            # 3. BFS pour trouver le chemin entre les deux pathways
            pathway_sequence = self._bfs(origin_pathway, dest_pathway)

        if pathway_sequence is None:
            return {
                'success': False,
                'route': None,
                'total_length': 0,
                'waypoints': [],
                'message': (
                    f"Aucun chemin trouvé entre {origin_pathway.name} "
                    f"et {dest_pathway.name}. Vérifiez les connexions entre pathways."
                )
            }

        # 4. Construire les waypoints à partir de la séquence de pathways
        waypoint_coords = self._build_waypoints(
            origin, destination, pathway_sequence
        )

        # 5. Calculer la longueur totale
        total_length = self._calculate_total_length(waypoint_coords)

        # 6. Désactiver les anciens tracés du câble
        cable.routes.filter(is_active=True).update(is_active=False)

        # 7. Créer le nouveau tracé en base de données
        route = CableRoute.objects.create(
            cable          = cable,
            is_active      = True,
            total_length_m = total_length,
            calculation_notes = (
                f"Tracé calculé automatiquement via BFS. "
                f"{len(pathway_sequence)} pathway(s) emprunté(s)."
            )
        )

        # 8. Créer les waypoints en base
        waypoints = []
        for i, coords in enumerate(waypoint_coords, start=1):
            wp = RouteWaypoint.objects.create(
                route   = route,
                order   = i,
                x       = coords['x'],
                y       = coords['y'],
                z       = coords['z'],
                pathway = coords.get('pathway'),
                label   = coords.get('label', '')
            )
            waypoints.append(wp)

        # 9. Mettre à jour la longueur du câble
        cable.designed_length_m = total_length
        cable.save(update_fields=['designed_length_m'])

        return {
            'success'      : True,
            'route'        : route,
            'total_length' : total_length,
            'waypoints'    : waypoints,
            'message'      : f"Tracé calculé avec succès. Longueur totale : {total_length:.1f} m"
        }

    # --------------------------------------------------------
    # ALGORITHME BFS
    # --------------------------------------------------------

    def _bfs(
        self,
        start: CablePathway,
        end: CablePathway
    ) -> Optional[list]:
        """
        Breadth-First Search (parcours en largeur) pour trouver
        le chemin le plus court entre deux pathways.

        Fonctionnement :
            1. On part du pathway de départ
            2. On explore tous ses voisins (connexions directes)
            3. Puis les voisins de ses voisins, etc.
            4. Le premier chemin qui atteint la destination est le plus court

        Returns:
            list[CablePathway] : Séquence de pathways du départ à la destination
            None               : Si aucun chemin trouvé
        """
        # File d'attente BFS : chaque élément est le chemin parcouru jusqu'ici
        queue = deque([[start]])

        # Ensemble des pathways déjà visités (pour éviter les boucles)
        visited = {start.id}

        # Construire un index pour accès rapide par id
        pathway_index = {p.id: p for p in self._pathways}

        while queue:
            # Prendre le premier chemin dans la file
            current_path = queue.popleft()
            current_node = current_path[-1]

            # Destination atteinte !
            if current_node.id == end.id:
                return current_path

            # Explorer les voisins (pathways connectés)
            for neighbor in current_node.connected_pathways.all():
                if neighbor.id not in visited:
                    visited.add(neighbor.id)
                    new_path = current_path + [neighbor]
                    queue.append(new_path)

        # Aucun chemin trouvé
        return None

    # --------------------------------------------------------
    # MÉTHODES UTILITAIRES
    # --------------------------------------------------------

    def _find_nearest_pathway(self, point: dict) -> Optional[CablePathway]:
        """
        Trouve le pathway le plus proche d'un point 3D.

        Pour chaque pathway, calcule la distance minimale entre
        le point et le segment [start, end] du pathway.

        Returns:
            CablePathway : Le pathway le plus proche
            None         : Si aucun pathway disponible
        """
        if not self._pathways:
            return None

        nearest  = None
        min_dist = float('inf')

        for pathway in self._pathways:
            dist = self._point_to_segment_distance(
                point,
                {'x': pathway.start_x, 'y': pathway.start_y, 'z': pathway.start_z},
                {'x': pathway.end_x,   'y': pathway.end_y,   'z': pathway.end_z}
            )
            if dist < min_dist:
                min_dist = dist
                nearest  = pathway

        return nearest

    def _point_to_segment_distance(
        self,
        point: dict,
        seg_start: dict,
        seg_end: dict
    ) -> float:
        """
        Calcule la distance minimale entre un point et un segment 3D.

        Utilise la projection orthogonale du point sur le segment.
        Si la projection est hors du segment, retourne la distance
        au point le plus proche (début ou fin du segment).
        """
        # Vecteur du segment
        dx = seg_end['x'] - seg_start['x']
        dy = seg_end['y'] - seg_start['y']
        dz = seg_end['z'] - seg_start['z']
        seg_len_sq = dx**2 + dy**2 + dz**2

        if seg_len_sq == 0:
            # Le segment est un point
            return self._euclidean_distance(point, seg_start)

        # Paramètre de projection (0 = début, 1 = fin, entre les deux = sur le segment)
        t = (
            (point['x'] - seg_start['x']) * dx +
            (point['y'] - seg_start['y']) * dy +
            (point['z'] - seg_start['z']) * dz
        ) / seg_len_sq

        t = max(0.0, min(1.0, t))  # Clamper entre 0 et 1

        # Point projeté sur le segment
        proj = {
            'x': seg_start['x'] + t * dx,
            'y': seg_start['y'] + t * dy,
            'z': seg_start['z'] + t * dz,
        }
        return self._euclidean_distance(point, proj)

    def _build_waypoints(
        self,
        origin: dict,
        destination: dict,
        pathway_sequence: list
    ) -> list:
        """
        Construit la liste ordonnée des waypoints à partir de la
        séquence de pathways trouvée par BFS.

        Stratégie :
        - WP1 = point d'origine exact
        - Pour chaque pathway : ajouter son point de début et de fin
        - Dernier WP = point de destination exact

        Returns:
            list[dict] : [{'x': ..., 'y': ..., 'z': ..., 'pathway': ..., 'label': ...}]
        """
        waypoints = []

        # Point de départ
        waypoints.append({
            'x': origin['x'],
            'y': origin['y'],
            'z': origin['z'],
            'pathway': None,
            'label': 'Départ'
        })

        # Points intermédiaires le long des pathways
        for i, pathway in enumerate(pathway_sequence):
            waypoints.append({
                'x': pathway.start_x,
                'y': pathway.start_y,
                'z': pathway.start_z,
                'pathway': pathway,
                'label': f'Entrée {pathway.name}'
            })
            waypoints.append({
                'x': pathway.end_x,
                'y': pathway.end_y,
                'z': pathway.end_z,
                'pathway': pathway,
                'label': f'Sortie {pathway.name}'
            })

        # Point de destination
        waypoints.append({
            'x': destination['x'],
            'y': destination['y'],
            'z': destination['z'],
            'pathway': None,
            'label': 'Arrivée'
        })

        return waypoints

    def _calculate_total_length(self, waypoints: list) -> float:
        """
        Calcule la longueur totale d'un tracé en additionnant
        les distances entre waypoints consécutifs.
        """
        total = 0.0
        for i in range(len(waypoints) - 1):
            total += self._euclidean_distance(waypoints[i], waypoints[i + 1])
        return round(total, 2)

    @staticmethod
    def _euclidean_distance(a: dict, b: dict) -> float:
        """Distance euclidienne 3D entre deux points."""
        return math.sqrt(
            (b['x'] - a['x'])**2 +
            (b['y'] - a['y'])**2 +
            (b['z'] - a['z'])**2
        )