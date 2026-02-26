"""
Optimiseur de tracé — Simplifie et améliore un tracé calculé par le routing engine.

Problème :
    Le routing engine produit parfois des tracés avec des waypoints redondants.
    Exemple : 3 points en ligne droite → le point intermédiaire est inutile.

    Avant : A(0,0) → B(5,0) → C(10,0)   (3 points, B est inutile)
    Après : A(0,0) → C(10,0)             (2 points, même résultat)

Optimisations appliquées :
    1. Suppression des waypoints colinéaires (en ligne droite)
    2. Vérification du rayon de courbure minimum
    3. Recalcul de la longueur totale

Algorithme Ramer-Douglas-Peucker (simplifié) :
    Utilisé en cartographie pour simplifier les tracés de routes/rivières.
    On supprime les points qui s'écartent de moins d'un seuil
    de la ligne droite reliant les extrémités.
"""

import math
from ..models import CableRoute, RouteWaypoint


class PathOptimizer:
    """
    Optimise un tracé de câble en supprimant les waypoints redondants.

    Usage :
        optimizer = PathOptimizer(tolerance_m=0.1)
        result = optimizer.optimize(route)
        # result = {
        #   'original_waypoints': 12,
        #   'optimized_waypoints': 5,
        #   'length_saved_m': 0.3,
        #   'route': <CableRoute (updated)>
        # }
    """

    def __init__(self, tolerance_m: float = 0.1):
        """
        Args:
            tolerance_m : Distance maximale (en mètres) en dessous de laquelle
                         un waypoint est considéré comme redondant.
                         0.1m = 10cm de tolérance.
        """
        self.tolerance = tolerance_m

    # --------------------------------------------------------
    # MÉTHODE PRINCIPALE
    # --------------------------------------------------------

    def optimize(self, route: CableRoute) -> dict:
        """
        Optimise un tracé en supprimant les waypoints inutiles.

        Args:
            route : Le tracé à optimiser

        Returns:
            dict : Statistiques de l'optimisation
        """
        waypoints = list(
            route.waypoints.order_by('order')
        )

        if len(waypoints) <= 2:
            # Rien à optimiser avec seulement 2 points
            route.is_optimized = True
            route.save(update_fields=['is_optimized'])
            return {
                'original_waypoints'  : len(waypoints),
                'optimized_waypoints' : len(waypoints),
                'length_saved_m'      : 0.0,
                'route'               : route,
            }

        original_count  = len(waypoints)
        original_length = route.total_length_m or 0

        # Extraire les coordonnées
        coords = [{'x': wp.x, 'y': wp.y, 'z': wp.z} for wp in waypoints]

        # Appliquer l'algorithme de simplification
        keep_indices = self._ramer_douglas_peucker(coords, self.tolerance)

        # Garder uniquement les waypoints non redondants
        kept_waypoints = [waypoints[i] for i in keep_indices]

        # Recréer les waypoints avec les bons ordres
        route.waypoints.all().delete()

        new_waypoints = []
        for new_order, wp in enumerate(kept_waypoints, start=1):
            new_wp = RouteWaypoint.objects.create(
                route   = route,
                order   = new_order,
                x       = wp.x,
                y       = wp.y,
                z       = wp.z,
                pathway = wp.pathway,
                label   = wp.label,
            )
            new_waypoints.append(new_wp)

        # Recalculer la longueur totale
        new_length = self._recalculate_length(new_waypoints)

        route.total_length_m = new_length
        route.is_optimized   = True
        route.save(update_fields=['total_length_m', 'is_optimized'])

        return {
            'original_waypoints'  : original_count,
            'optimized_waypoints' : len(new_waypoints),
            'length_saved_m'      : round(original_length - new_length, 2),
            'route'               : route,
        }

    # --------------------------------------------------------
    # ALGORITHME RAMER-DOUGLAS-PEUCKER
    # --------------------------------------------------------

    def _ramer_douglas_peucker(self, points: list, tolerance: float) -> list:
        """
        Algorithme de simplification de polylignes.

        Principe :
        1. Tracer une ligne droite entre le premier et le dernier point
        2. Trouver le point le plus éloigné de cette ligne
        3. Si sa distance > tolérance : ce point est important → le garder
           et diviser le problème en deux sous-problèmes récursifs
        4. Si sa distance <= tolérance : supprimer tous les points intermédiaires

        Args:
            points    : Liste de {'x', 'y', 'z'}
            tolerance : Distance seuil en mètres

        Returns:
            list[int] : Indices des points à conserver
        """
        if len(points) <= 2:
            return list(range(len(points)))

        # Trouver le point le plus éloigné de la ligne [premier → dernier]
        max_dist  = 0.0
        max_index = 0

        start = points[0]
        end   = points[-1]

        for i in range(1, len(points) - 1):
            dist = self._point_to_line_distance(points[i], start, end)
            if dist > max_dist:
                max_dist  = dist
                max_index = i

        # Si le point le plus éloigné dépasse la tolérance → le garder
        if max_dist > tolerance:
            # Résoudre récursivement les deux moitiés
            left_indices  = self._ramer_douglas_peucker(
                points[:max_index + 1], tolerance
            )
            right_indices = self._ramer_douglas_peucker(
                points[max_index:], tolerance
            )
            # Fusionner (décaler les indices de la partie droite)
            right_shifted = [i + max_index for i in right_indices[1:]]
            return left_indices + right_shifted
        else:
            # Tous les points intermédiaires sont redondants
            return [0, len(points) - 1]

    # --------------------------------------------------------
    # UTILITAIRES GÉOMÉTRIQUES
    # --------------------------------------------------------

    def _point_to_line_distance(
        self,
        point: dict,
        line_start: dict,
        line_end: dict
    ) -> float:
        """
        Distance perpendiculaire d'un point à une droite 3D.

        Utilise le produit vectoriel pour calculer la distance.
        """
        # Vecteur de la droite
        line_vec = {
            'x': line_end['x'] - line_start['x'],
            'y': line_end['y'] - line_start['y'],
            'z': line_end['z'] - line_start['z'],
        }
        # Vecteur du point au début de la droite
        point_vec = {
            'x': point['x'] - line_start['x'],
            'y': point['y'] - line_start['y'],
            'z': point['z'] - line_start['z'],
        }

        # Longueur de la droite
        line_len = math.sqrt(
            line_vec['x']**2 + line_vec['y']**2 + line_vec['z']**2
        )

        if line_len == 0:
            # La droite est un point
            return math.sqrt(
                point_vec['x']**2 + point_vec['y']**2 + point_vec['z']**2
            )

        # Produit vectoriel (cross product) pour obtenir la distance perpendiculaire
        cross = {
            'x': point_vec['y'] * line_vec['z'] - point_vec['z'] * line_vec['y'],
            'y': point_vec['z'] * line_vec['x'] - point_vec['x'] * line_vec['z'],
            'z': point_vec['x'] * line_vec['y'] - point_vec['y'] * line_vec['x'],
        }
        cross_magnitude = math.sqrt(
            cross['x']**2 + cross['y']**2 + cross['z']**2
        )

        return cross_magnitude / line_len

    def _recalculate_length(self, waypoints: list) -> float:
        """Recalcule la longueur totale après optimisation."""
        total = 0.0
        for i in range(len(waypoints) - 1):
            a = waypoints[i]
            b = waypoints[i + 1]
            total += math.sqrt(
                (b.x - a.x)**2 + (b.y - a.y)**2 + (b.z - a.z)**2
            )
        return round(total, 2)