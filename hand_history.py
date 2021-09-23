#!/usr/bin/env python3
import re
import sys
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass

@dataclass 
class Pot:
    amounts: Dict[str, float]
    winners: Dict[str, float]
    at_showdown: Set[str]

@dataclass
class HandLog:
    has_showdown = False
    blinds: Dict[str, float] 
    at_table: Set[str]
    vpip: Set[str]
    pots: List[Pot]
    
    @staticmethod
    def empty_hand():
        return HandLog({}, set(), set(), [])

    def is_empty(self):
        return not (self.blinds or self.at_table or self.vpip or self.pots)

@dataclass
class HandHistory:
    hand_logs: List[HandLog]
    adds: List[Tuple[str, float]]


def read_hand_history(f) -> HandHistory:
    hands: List[HandLog] = []
    hand_start_re = re.compile(r"Hand #")
    winner_re = re.compile(r"(?P<name>[a-zA-Z0-9_]+)\s+(?P<win_type>wins|splits)\s+.*\s+\((?P<amount>[0-9.]+)\).*")
    vpip_re = re.compile(r"(?P<name>[a-zA-Z0-9_]+)\s+(bets|calls|raises to)\s+(?P<amount>[0-9.]+)")
    blinds_in = re.compile(r"(?P<name>[a-zA-Z0-9_]+)\s+(posts (small|big) blind)\s+(?P<amount>[0-9.]+)")
    rake_re = re.compile(r"Rake\s+\(([0-9.]+)\)\s*Pot\s+\([0-9.]+\)\s+Players\s+\((?P<players>[^)]+)\)")
    part_re = re.compile(r"Seat\s*.*:\s+(?P<name>[a-zA-Z0-9_]+)")
    show_re = re.compile(r"(?P<name>[a-zA-Z0-9_]+)\s+shows.*")
    showdown_re = re.compile(r"Show Down")
    adds_re = re.compile(r"(?P<name>[a-zA-Z0-9_]+)\s+adds\s+(?P<amount>[0-9.]+)\s+chips.*")
    hand = HandLog.empty_hand()
    shows = []
    pot = None
    player_adds = []
    for i, line in enumerate(f, 1):
        if line.strip() == "":
            if not hand.is_empty():
                hands.append(hand)
            hand = HandLog.empty_hand()
        hand_start = hand_start_re.search(line)
        if hand_start:
            hand = HandLog.empty_hand()
            shows = []
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
                pot = Pot({}, {}, set())
            pot.winners[name] = amount
            continue
        show_match = show_re.search(line)
        if show_match:
            shows.append(show_match.group("name"))
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
            assert(isinstance(pot, Pot))
            players = rake_match.group("players").split(", ")
            players = [p.split(": ") for p in players]
            pot.amounts = {name: float(amt) / 10.0 for (name, amt) in players if amt != "0"}
            pot.at_showdown = set(shows or [])
            hand.pots.append(pot)
            pot = None
            continue

        adds_match = adds_re.search(line)
        if adds_match:
            player = adds_match.group("name")
            amount = float(adds_match.group("amount")) / 10.0
            player_adds.append((player, amount))

    return HandHistory(hands, player_adds)

def player_info(hands: List[HandLog], player: str):
    total_hands = sum(1 for hand in hands if player in hand.at_table)
    num_showdown = sum(1 for hand in hands if hand.has_showdown and any(player in pot.at_showdown for pot in hand.pots))
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
    max_pot = 0.0
    min_pot = 0.0
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
        amount_net = amount_won - amount_bet
        net += amount_net
        max_pot = max(max_pot, amount_net)
        min_pot = min(min_pot, amount_net)

    print("{}: ".format(player))
    print("  Net Winnings: ${:.2f}".format(net))
    print("  # of Hands At Table: {}".format(total_hands))
    print("  # of Hands in: {} ({:.2f}%)".format(num_part, 100 * num_part / total_hands))
    print("  # of Hands VPiP: {} ({:.2f}%)".format(num_vpip, 100 * num_vpip / total_hands))
    print("  # of Hands @ Showdown: {} ({:.2f}% of hands VPiP)".format(num_showdown, 100 * num_showdown / num_vpip))
    print("  # of Hands won: {} ({:.2f}% of hands in, {:.2f}% of hands VPiP)".format(num_hands_won, 100*num_hands_won / num_part, 100*num_hands_won / num_vpip))
    print("  # of Hands won at showdown: {} ({:.2f}% of hands in, {:.2f}% of hands in at showdown)".format(
        num_hands_won_showdown, 100 * num_hands_won_showdown / num_part, 100 * num_hands_won_showdown / num_showdown))
    print("  Average Pot Won: (Gross: ${:.2f}, Net: ${:.2f}) on {} hands".format(gross_won / num_hands_won, net_won / num_hands_won, num_hands_won))
    print("  Max Pot Won (Net): ${:.2f}".format(max_pot))
    print("  Average Pot Lost: ${:.2f} on {} hands".format(net_lost / num_hands_lost, num_hands_lost))
    print("  Average Pot Lost (VPiP only): ${:.2f} on {} hands".format((net_lost - blinds_paid) / num_hands_lost_vpip, num_hands_lost_vpip))
    print("  Max Pot Lost (Net): ${:.2f}".format(min_pot))

if __name__ == "__main__":
    hand_history_file = sys.argv[1]
    hand_history = read_hand_history(open(hand_history_file))
    all_players = set()
    for hand in hand_history.hand_logs:
        all_players = all_players | set(hand.blinds.keys())
    for player in all_players:
        player_info(hand_history.hand_logs, player)
        print("")
    

        
