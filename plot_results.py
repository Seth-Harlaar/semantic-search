import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Read the CSV
df = pd.read_csv("results.csv")

# Make sure expected_id is a string
df["expected_id"] = df["expected_id"].astype(str)

# Create a test identifier to show both test text & expected id
df["test_case"] = df.apply(lambda x: f"{x['test_text']} (expected {x['expected_id']})", axis=1)

# Melt the dataframe for easier plotting
melted = df.melt(
    id_vars=["metadata_type", "test_case"],
    value_vars=["rank_1_distance", "rank_2_distance", "rank_3_distance"],
    var_name="rank",
    value_name="distance"
)

# Rank as nicer labels
melted["rank"] = melted["rank"].map({
    "rank_1_distance": "Rank 1",
    "rank_2_distance": "Rank 2",
    "rank_3_distance": "Rank 3"
})

# Set up the plot
plt.figure(figsize=(14, 8))
sns.set(style="whitegrid")

# Plot using seaborn
sns.barplot(
    data=melted,
    x="test_case",
    y="distance",
    hue="metadata_type",
    ci=None
)

plt.xticks(rotation=45, ha='right')
plt.xlabel("Test Case")
plt.ylabel("Distance")
plt.title("Embedding Search Distances per Metadata Type")
plt.tight_layout()

plt.legend(title="Metadata Type")
plt.show()
