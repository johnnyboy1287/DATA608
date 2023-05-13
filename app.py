import dash
from dash import dcc, html
import plotly.express as px
import pandas as pd
import requests





######################################################################################################

# create the Dash app
app = dash.Dash(__name__)

# define the layout
app.layout = html.Div([
    html.H1('NYC Tree Data'),
    html.Label('Select a borough:'),
    dcc.RadioItems(
        id='borough-radio',
        options=[
            {'label': 'Bronx', 'value': 'Bronx'},
            {'label': 'Brooklyn', 'value': 'Brooklyn'},
            {'label': 'Manhattan', 'value': 'Manhattan'},
            {'label': 'Queens', 'value': 'Queens'},
            {'label': 'Staten Island', 'value': 'Staten Island'}
        ],
        value='Bronx'
    ),
    dcc.Graph(id='tree-health'),
    html.H2('Steward Effectiveness'),
    dcc.Graph(id='steward-effectiveness'),  # New plot for steward effectiveness
])



########################################################################################################


# define the callback to update the tree health data
@app.callback(
    dash.dependencies.Output('tree-health', 'figure'),
    [dash.dependencies.Input('borough-radio', 'value')]
)


def tree_health(borough):

    
    # Set the URL and query parameters
    url = 'https://data.cityofnewyork.us/resource/nwxe-4ae8.json'
    query_params = {'$select': 'boroname, spc_common, health, count(tree_id)',
                    '$where': f"boroname = '{borough}' AND health IS NOT NULL",
                    '$group': 'boroname, spc_common, health',
                    '$order': 'boroname, spc_common, health'}
    
    response = requests.get(url, params=query_params)
    content = response.content.decode('utf-8')
    trees = pd.read_json(content)
    
    # Rename the count column to a more descriptive name
    trees.rename(columns={'count_tree_id': 'count'}, inplace=True)
    
    # Pivot the data to make the tree species the index, and the health categories as columns
    trees_pivot = pd.pivot_table(trees, values='count', index=['boroname', 'spc_common'], columns='health', fill_value=0)
    
    # Reset the index to make the borough and tree species columns again
    trees_pivot = trees_pivot.reset_index()
    
    # Add a total column to your pivot table
    trees_pivot['Total'] = trees_pivot[['Fair', 'Good', 'Poor']].sum(axis=1)
    
    # Melt the DataFrame again, this time including the total column
    trees_melt = trees_pivot.melt(id_vars=['boroname', 'spc_common', 'Total'], value_vars=['Fair', 'Good', 'Poor'], var_name='health', value_name='count')
    
    # Calculate the proportion for each row
    trees_melt['proportion'] = trees_melt['count'] / trees_melt['Total']
    
    # Determine the ten most populous tree species
    top_species = trees_pivot.nlargest(10, 'Total').spc_common
    
    # Filter the melted DataFrame to only include these species
    top_trees_melt = trees_melt[trees_melt.spc_common.isin(top_species)]
    
    # Create the stacked bar plot
    fig = px.bar(top_trees_melt, x='spc_common', y='proportion', color='health', 
                 title= f'Tree Health in {borough} for Top 10 Species', height=400, barmode='stack',
                 color_discrete_map={'Poor': 'red', 'Fair': 'yellow', 'Good': 'green'})
    
    # Update the layout
    fig.update_layout(xaxis={'categoryorder':'total descending'}, width=800)
    
    return fig

#######################################################################################################
@app.callback(
    dash.dependencies.Output('steward-effectiveness', 'figure'),
    [dash.dependencies.Input('borough-radio', 'value')]
    
)

def update_steward(borough):

    url = 'https://data.cityofnewyork.us/resource/nwxe-4ae8.json'
    query_params = {'$select': 'boroname, spc_common, steward, health, count(tree_id)',
                    '$where': f"boroname = '{borough}' AND steward IS NOT NULL AND health IS NOT NULL",
                    '$group': 'boroname, spc_common, steward, health',
                    '$order': 'boroname, spc_common, steward, health'}
    
    response = requests.get(url, params=query_params)
    content = response.content.decode('utf-8')
    trees = pd.read_json(content)
    
    # Rename the count column to a more descriptive name
    trees.rename(columns={'count_tree_id': 'count'}, inplace=True)
    
    # Pivot the data to make the tree species and steward the index, and the health categories as columns
    trees_pivot = pd.pivot_table(trees, values='count', index=['boroname', 'spc_common', 'steward'], columns='health', fill_value=0)
    
    # Reset the index to make the borough, tree species, and steward columns again
    trees_pivot = trees_pivot.reset_index()
    
    # Add a total column to your pivot table
    trees_pivot['Total'] = trees_pivot[['Fair', 'Good', 'Poor']].sum(axis=1)
    
    # Determine the ten most populous tree species
    top_species = trees_pivot.nlargest(10, 'Total').spc_common

    # Melt the DataFrame again, this time including the total column
    trees_melt = trees_pivot.melt(id_vars=['boroname', 'spc_common', 'steward', 'Total'], value_vars=['Fair', 'Good', 'Poor'], var_name='health', value_name='count')
    
    # Calculate the proportion for each row
    trees_melt['proportion'] = trees_melt['count'] / trees_melt['Total']
    
    # Filter the melted DataFrame to only include the top species
    top_trees_melt = trees_melt[trees_melt.spc_common.isin(top_species)]
    
    # Create the faceted bar plot
    fig2 = px.bar(top_trees_melt, x='steward', y='proportion', color='health', facet_col='spc_common', facet_col_wrap=4,
                 title=f'Steward Effectiveness in {borough} for Top 10 Species', height=400,
                 color_discrete_map={'Poor': 'red', 'Fair': 'yellow', 'Good': 'green'})
    
    # Update the layout for each subplot
    fig2.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1],))
    
    
    
    
    return fig2






# run the app
if __name__ == '__main__':
    app.run_server(debug=True)
