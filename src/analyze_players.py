"""Analyze players bets"""
import datetime
import os
import pandas as pd

import simplejson

# workaround to load big numbers (?)
pd.io.json._json.loads = lambda s, *a, **kw: simplejson.loads(s)


def load_player_data(json_file: str) -> pd.DataFrame:
    """
    Load player data from json file
    :param json_file: Path to json file
    :return: Dataframe with player data
    """
    # basePath = os.path.dirname(os.path.abspath(__file__))
    #
    # path = basePath + f'\\{players_data_folder}\\' + json_file
    # print(f"Loading {path}")
    df = pd.read_json(json_file)

    # Delete transactions with error
    print(f"Deleting {df[df['isError'] == 1].shape[0]} records from player data, where transaction was an error")
    df = df[df['isError'] == 0]

    df = df.drop(columns=['blockNumber', 'timeStamp', 'hash', 'nonce', 'blockHash',
                          'transactionIndex', 'from', 'to', 'value', 'gas', 'gasPrice', 'isError',
                          'txreceipt_status', 'contractAddress', 'cumulativeGasUsed',
                          'gasUsed', 'confirmations', 'methodId', 'input'])
    df = df.sort_values('epoch')

    return df


def load_rounds_data(path: str) -> pd.DataFrame:
    """
    Load rounds data from csv file
    :param path: Path to csv file
    :return: Dataframe with rounds data
    """
    df = pd.read_csv(path, delimiter='\t')
    print(f"There are {df[df.columns[0]].count()} records in rounds data total and"
          f" {df[df['position'].isnull()].shape[0]} records with unspecified position (NaN), probably failed")
    df = df[~df['position'].isnull()]

    return df


def analyze_player(player_df: pd.DataFrame, rounds_df: pd.DataFrame, check_from: int = None) -> pd.DataFrame:
    """
    Analyze player bets
    :param player_df: Dataframe with player bets
    :param rounds_df: Dataframe with rounds data
    :param check_from: Check only transactions after this timestamp (optional)
    :return: Dataframe with player bets and rounds data merged
    """
    # Select only needed timeline rows
    rounds_df = rounds_df[rounds_df['epoch'].isin(player_df['epoch'])]

    number_of_records_before_cropping = player_df[player_df.columns[0]].count()

    # Delete rows that are not in the rounds data
    player_df = player_df[player_df['epoch'].isin(rounds_df['epoch'])]
    number_of_records_after_cropping = player_df[player_df.columns[0]].count()

    print(f"There are {number_of_records_before_cropping} player bets in total,"
          f" {number_of_records_before_cropping - number_of_records_after_cropping} bets were not in the rounds data")
    # print("--------- timeline df after cropping -------------")
    # print(timeline_df)
    #
    # print(player_df)

    # Rename columns before merging the dfs
    player_df = player_df.rename(columns={'functionName': 'player_bet'})

    final_df = pd.merge(rounds_df, player_df, on='epoch')

    # Check from (unix timestamp)
    if check_from:
        # try:
        #     final_df = final_df[final_df['closeAt'] >= float(check_from)]
        #     print(f"Checking only transactions after {datetime.datetime.utcfromtimestamp(int(check_from)).strftime('%Y-%m-%d %H:%M:%S')}")
        # except:
        final_df = final_df[final_df['close_timestamp'] >= check_from]
        print(f"Checking only transactions after"
              f" {datetime.datetime.utcfromtimestamp(check_from).strftime('%Y-%m-%d %H:%M:%S')}")

    return final_df[['epoch', 'player_bet', 'bet_amount']]


def create_final_csv_files(player_data_dir: str, final_data_dir: str, rounds_df: pd.DataFrame,
                           check_from: int = None) -> None:
    """
    Create final csv file with player bets and rounds data merged
    :param final_data_dir: Directory to save the final CSV files
    :param player_data_dir: Directory with player data JSON files
    :param rounds_df: Dataframe with rounds data
    :param check_from: Check only transactions after this timestamp (optional)
    :return: None
    """
    # Get all player data files with their full path
    player_data_files = [os.path.join(player_data_dir, f) for f in os.listdir(player_data_dir) if
                         os.path.isfile(os.path.join(player_data_dir, f))]

    # df_player_bet = rounds_df.copy()
    # df_bet_amount = rounds_df.copy()

    merged_player_bet = rounds_df.copy()
    merged_bet_amount = rounds_df.copy()

    for player_data_file in player_data_files:
        print(f"Analyzing {player_data_file}")
        player_df = load_player_data(player_data_file)
        calculated_player_df = analyze_player(player_df, rounds_df, check_from)

        filename = os.path.basename(player_data_file).replace('.json', '')

        # calculated_player_df = calculated_player_df.rename(columns={'player_bet': filename})

        # calculated_player_df = calculated_player_df[['epoch', filename]]

        # Merge df_player_bet and df_bet_amount with calculated_player_df on epoch
        merged_player_bet = pd.merge(merged_player_bet, calculated_player_df[['epoch', 'player_bet']], on='epoch', how='left')
        merged_bet_amount = pd.merge(merged_bet_amount, calculated_player_df[['epoch', 'bet_amount']], on='epoch', how='left')

        merged_player_bet = merged_player_bet.rename(columns={'player_bet': filename})
        merged_bet_amount = merged_bet_amount.rename(columns={'bet_amount': filename})

    merged_player_bet.set_index('epoch', inplace=True)
    merged_bet_amount.set_index('epoch', inplace=True)

    # Delete the Unnamed column
    merged_player_bet = merged_player_bet.loc[:, ~merged_player_bet.columns.str.contains('Unnamed')]
    merged_bet_amount = merged_bet_amount.loc[:, ~merged_bet_amount.columns.str.contains('Unnamed')]

    merged_player_bet.to_csv(final_data_dir + 'final_player_bet.csv')
    merged_bet_amount.to_csv(final_data_dir + 'final_bet_amount.csv')


if __name__ == "__main__":
    # Downloading players bet history settings
    players_data_folder = '../data/players_data/'

    # Download rounds settings
    rounds_file = '../data/rounds_data/final_rounds_data.csv'

    # Final data
    final_data_folder = '../data/merged_data/'

    rounds_df = load_rounds_data(rounds_file)

    create_final_csv_files(players_data_folder, final_data_folder, rounds_df)
