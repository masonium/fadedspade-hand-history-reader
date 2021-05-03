import re
import sys
from typing import List, Dict, Set
from dataclasses import dataclass

@dataclass 
class Pot:
    amounts: Dict[str, float]
    winners: Dict[str, float]

@dataclass
class HandLog:
    has_showdown = False
    blinds: Dict[str, float] 
    at_table: Set[str]
    vpip: Set[str]
    pots: List[Pot]

def read_hand_history(f) -> List[HandLog]:
    hands: List[HandLog] = []
    hand_start_re = re.compile(r"Hand #")
    winner_re = re.compile(r"(?P<name>[a-zA-Z0-9_]+)\s+(?P<win_type>wins|splits)\s+.*\s+\((?P<amount>[0-9.]+)\).*")
    vpip_re = re.compile(r"(?P<name>[a-zA-Z0-9_]+)\s+(bets|calls|raises to)\s+(?P<amount>[0-9.]+)")
    blinds_in = re.compile(r"(?P<name>[a-zA-Z0-9_]+)\s+(posts (small|big) blind)\s+(?P<amount>[0-9.]+)")
    rake_re = re.compile(r"Rake\s+\(([0-9.]+)\)\s*Pot\s+\([0-9.]+\)\s+Players\s+\((?P<players>[^)]+)\)")
    part_re = re.compile(r"Seat\s*.*:\s+(?P<name>[a-zA-Z0-9_]+)")
    showdown_re = re.compile(r"Show Down")
    hand = None
    pot = None
    for line in f:
        if line.strip() == "":
            if hand is not None:
                hands.append(hand)
            hand = None
        hand_start = hand_start_re.search(line)
        if hand_start:
            hand = HandLog({}, set(), set(), [])
            continue
        part_match = part_re.search(line)
        if part_match:
            name = part_match.group("name")
            hand.at_table.add(name)
            continue
        if showdown_re.search(line):
            hand.has_showdown = True
            continue
        winner_match = winner_re.search(line)
        if winner_match:
            name = winner_match.group("name")
            amount = float(winner_match.group("amount")) / 10.0
            if pot is None:
                pot = Pot({}, {})
            pot.winners[name] = amount
            continue
        vpip_match = vpip_re.search(line)
        if vpip_match:
            name = vpip_match.group("name")
            hand.vpip.add(name)
            continue
        blind_match = blinds_in.search(line)
        if blind_match:
            name = blind_match.group("name")
            amount = float(blind_match.group("amount")) / 10.0
            hand.blinds[name] = amount
            continue
        rake_match = rake_re.search(line)
        if rake_match:
            players = rake_match.group("players").split(", ")
            players = [p.split(": ") for p in players]
            pot.amounts = {name: float(amt) / 10.0 for (name, amt) in players if amt != "0"}
            hand.pots.append(pot)
            pot = None
            continue

    return hands

def player_info(hands: List[HandLog], player: str):
    total_hands = sum(1 for hand in hands if player in hand.at_table)
    total_showdown_hands = sum(1 for hand in hands if player in hand.at_table and hand.has_showdown)
    num_vpip = sum(1 for hand in hands if player in hand.vpip)
    num_part = sum(1 for hand in hands if any(player in pot.amounts for pot in hand.pots))
    num_hands_won = 0
    num_hands_lost = 0
    num_hands_lost_vpip = 0
    num_hands_won_showdown = 0
    net = 0.0
    net_won = 0.0
    gross_won = 0.0
    net_lost = 0.0
    blinds_paid = 0.0
    for hand in hands:
        amount_won = 0.0
        amount_bet = 0.0
        blinds_paid += hand.blinds.get(player, 0.0)
        for pot in hand.pots:
            amount_won += pot.winners.get(player, 0.0)
            amount_bet += pot.amounts.get(player, 0.0)
        if amount_won > 0.0 and amount_won > amount_bet:
            num_hands_won += 1
            if hand.has_showdown:
                num_hands_won_showdown += 1
            gross_won += amount_won
            net_won += amount_won - amount_bet
        elif amount_bet > 0.0:
            net_lost += amount_bet - amount_won
            num_hands_lost += 1
            if player in hand.vpip:
                num_hands_lost_vpip += 1
        net += amount_won - amount_bet
    print("{}: ".format(player))
    print("  Net Winnings: ${:.2f}".format(net))
    print("  # of Hands At Table: {}".format(total_hands))
    print("  # of Hands in: {} ({:.2f}%)".format(num_part, 100 * num_part / total_hands))
    print("  # of Hands VPiP: {} ({:.2f}%)".format(num_vpip, 100 * num_vpip / total_hands))
    print("  # of Hands won: {} ({:.2f}% of hands in)".format(num_hands_won, 100*num_hands_won / num_part))
    print("  # of Hands won at showdown: {} ({:.2f}% of hands in)".format(
        num_hands_won_showdown, 100 * num_hands_won_showdown / num_part))
    print("  Average Pot Won: (Gross: ${:.2f}, Net: ${:.2f})".format(gross_won / num_hands_won, net_won / num_hands_won))
    print("  Average Pot Lost: ${:.2f} on {} hands".format(net_lost / num_hands_lost, num_hands_lost))
    print("  Average Pot Lost (VPiP only): ${:.2f} on {} hands".format((net_lost - blinds_paid) / num_hands_lost_vpip, num_hands_lost_vpip))

if __name__ == "__main__":
    hand_history_file = sys.argv[1]
    hands = read_hand_history(open(hand_history_file))
    all_players = set()
    for hand in hands:
        all_players = all_players | set(hand.blinds.keys())
    for player in all_players:
        player_info(hands, player)
        print("")
