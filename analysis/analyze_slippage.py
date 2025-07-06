import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def analyze_slippage(file_path):
    """
    Analyzes the slippage from backtest results to determine optimal filtering thresholds.

    Args:
        file_path (str): The path to the backtest results CSV file.
    """
    # Load the data
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
        return

    # --- Data Cleaning and Preparation ---
    # Extract the numeric entry price
    df['Entry Price'] = df['Entry Price & Time'].apply(lambda x: float(str(x).split('@')[0].strip()))

    # Determine trade direction (Buy/Sell)
    df['Direction'] = df['Level Broken'].apply(lambda x: 'BUY' if x in ['PMH', 'PDH'] else 'SELL')

    # Calculate slippage
    # For BUY trades (breaking resistance), a lower entry price is better.
    # For SELL trades (breaking support), a higher entry price is better.
    # We'll define slippage as the difference from the ideal entry at the retested level.
    # A positive slippage value will always indicate a worse entry price.
    df['Slippage'] = df.apply(
        lambda row: row['Entry Price'] - row['Retested Level'] if row['Direction'] == 'BUY' 
        else row['Retested Level'] - row['Entry Price'],
        axis=1
    )

    # Separate wins and losses
    wins = df[df['Result'] == 'WIN']
    losses = df[df['Result'] == 'LOSS']

    # --- Analysis and Visualization ---
    print("--- Slippage Analysis ---")
    print(f"Total Trades: {len(df)}")
    print(f"Wins: {len(wins)}, Losses: {len(losses)}\n")

    print("Slippage Statistics for WINNING trades:")
    print(wins['Slippage'].describe())
    print("\nSlippage Statistics for LOSING trades:")
    print(losses['Slippage'].describe())

    # Plotting the distributions
    plt.style.use('seaborn-v0_8-darkgrid')
    fig, ax = plt.subplots(figsize=(12, 7))

    sns.histplot(wins['Slippage'], color='green', label='Wins', kde=True, ax=ax, stat='density', common_norm=False)
    sns.histplot(losses['Slippage'], color='red', label='Losses', kde=True, ax=ax, stat='density', common_norm=False)

    ax.set_title('Distribution of Entry Slippage for Wins and Losses', fontsize=16)
    ax.set_xlabel('Slippage (in points)', fontsize=12)
    ax.set_ylabel('Density', fontsize=12)
    ax.legend()
    
    # Add vertical lines for mean slippage
    ax.axvline(wins['Slippage'].mean(), color='darkgreen', linestyle='--', label=f"Win Mean: {wins['Slippage'].mean():.2f}")
    ax.axvline(losses['Slippage'].mean(), color='darkred', linestyle='--', label=f"Loss Mean: {losses['Slippage'].mean():.2f}")
    ax.legend()

    print("\n--- Interpretation ---")
    print("The plot shows the distribution of entry slippage for winning and losing trades.")
    print("Observe the overlap and the means. A good filter would cut off a larger portion of the red distribution (losses) than the green one (wins).")
    print("Look for a slippage value on the x-axis where the red curve is significantly higher than the green curve.")

    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    # Path to the results file relative to the project root
    results_file = 'backtest_results_20240101_to_20241231.csv'
    analyze_slippage(results_file)
