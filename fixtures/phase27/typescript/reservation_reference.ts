export type ReservationState = 'held' | 'expired' | 'released';
export type Reservation = { state: ReservationState; units: number };
export type Inventory = { available: number };

export function releaseReservation(reservation: Reservation, inventory: Inventory): number {
  if (reservation.state === 'held') {
    inventory.available += reservation.units;
    reservation.state = 'released';
  }
  return inventory.available;
}
