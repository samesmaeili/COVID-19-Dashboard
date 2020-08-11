from collections import OrderedDict
import plotly.graph_objects as go
import pandas as pd
import matplotlib.pyplot as plt;
plt.rcdefaults()
from plotly.subplots import make_subplots
import plotly.express as px
from datetime import datetime
import requests

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from sodapy import Socrata
import calendar
import datetime
from datetime import datetime as dt, timedelta


app = dash.Dash(__name__)
server = app.server

app.title = "COVID-19 State Comparison"

#styling variables
font_size_nums = 30
font_size_text = 20
font_drop_down__size = 18
font_title_above_drop_down = font_size_text*1.3
stateTitleSize = 22
font_subTitle_size = 16
margin_dic = margin = dict(l=20, r=20, b=20, t=80)

last_day_updated = datetime.date.today()

def dfStateTotalsRequest():
    #getting covid data from web service (contains confirmed, recovered, deaths on all countries/states)
    raw= requests.get("https://services1.arcgis.com/0MSEUqKaxRlEPj5g/arcgis/rest/services/Coronavirus_2019_nCoV_Cases/FeatureServer/1/query?where=1%3D1&outFields=*&outSR=4326&f=json")
    raw_json = raw.json()
    return pd.DataFrame(raw_json["features"])

df = dfStateTotalsRequest()


def dfStateAgeGroupRequest():
    #getting another set of covid data from cdc website (breaks down death cases by age group for each state)
    #raw2 = requests.get("https://data.cdc.gov/resource/9bhg-hcku.json")
    #raw_json2 = raw2.json()

    # Unauthenticated client only works with public data sets. Note 'None'
    # in place of application token, and no username or password:
    client = Socrata("data.cdc.gov", None)

    # Example authenticated client (needed for non-public datasets):
    # client = Socrata(data.cdc.gov,
    #                  MyAppToken,
    #                  userame="user@example.com",
    #                  password="AFakePassword")

    # First 1500 results, returned as JSON from API / converted to Python list of
    # dictionaries by sodapy.
    raw2 = client.get("9bhg-hcku", limit=1500)
    # Convert to pandas DataFrame
    df2 = pd.DataFrame.from_records(raw2)

    #df2 = pd.DataFrame(raw_json2)
    #transform secondary data
    df3 = df2[["state", "age_group", "covid_19_deaths"]]
    df4 = df3[df3.state != "United States"]
    df5 = df4[df4.state != "United States Total"]
    df6 = df5[~df5.state.str.contains("Total")]
    df6 = df6[~(df6.age_group.str.contains("all ages") |df6.age_group.str.contains("All ages"))]
    df6["covid_19_deaths"] = df6["covid_19_deaths"].astype(float)
    df6 = df6.drop(df6.index[df6.state == 'New York City']) #remove nyc, since ny alread in data set
    return df6

df6 = dfStateAgeGroupRequest()

#aggregate by state
# df_total1 = df6.groupby(["state", "age_group"], as_index=False).agg(
#     {
#         "covid_19_deaths": "sum",
#     }
# )

def getStatesInOrder(df6):
    stateSet = set()
    for index,row in df6.iterrows():
        co = row['state']
        stateSet.add(co)
    return sorted(stateSet) #sort states

orderedState = getStatesInOrder(df6)


def transformTotalStateDF(df):

    #transform data
    data_list = df["attributes"].tolist()
    df_final = pd.DataFrame(data_list)
    df_final.set_index("OBJECTID")
    df_final = df_final[["Country_Region", "Province_State", "Confirmed", "Deaths", "Recovered", "Last_Update"]]
    df_final.head()

    #clean data
    def convertTime(t):
        t = int(t)
        return dt.fromtimestamp(t)

    df_final = df_final.dropna(subset=["Last_Update"]) #drop values with na in last update field
    df_final["Province_State"].fillna(value="", inplace=True) #add empty string for na values in Province State

    df_final["Last_Update"]= df_final["Last_Update"]/1000 #convert millsecond time in last_update field
    df_final["Last_Update"] = df_final["Last_Update"].apply(convertTime)

    return df_final

df_final = transformTotalStateDF(df)

def onlyUSStates(df_final):
    #states df
    df_states = df_final.loc[df_final["Country_Region"] == "US"]
    return df_states

df_states = onlyUSStates(df_final)

def getSource():
    return "Sources: Esri & CDC | "

def getLastTime(df_states):
    last_updated =  df_states.iloc[0]["Last_Update"]

    #last updated
    dateSplit = str(last_updated).split(' ')
    date1 = dt.strptime(dateSplit[0], "%Y-%m-%d").strftime("%m-%d-%Y")
    date1Converted = dt.strptime(date1, "%m-%d-%Y")
    month = calendar.month_name[date1Converted.month]
    day = date1Converted.day
    year = date1Converted.year
    joinDates = ', '.join([month + " " + str(day), str(year)])
    last_updated_string = "Last Updated: " + joinDates
    return last_updated_string

subTitle = getSource() +  getLastTime(df_states)


#Contains Confirmed/Death counts for each state
def dicConfirmedDeathsStates(df_states):
    state_dic = {}
    for index, row in df_states.iterrows():
        state_dic[row["Province_State"]] = (row["Confirmed"], row["Deaths"])
    return state_dic

state_dic = dicConfirmedDeathsStates(df_states)


# ------------------------------------------------------------------------------
# App layout
app.layout = html.Div([

    html.H1("COVID-19 State Comparison", style={'text-align': 'center', 'font-family':'Arial', 'margin-bottom':'0'}),
    html.Div(id='output_container', children=[subTitle] , style={'font-size': font_subTitle_size, 'font-family': 'arial',
                                       'margin-bottom': '0px', 'text-align': 'center'}),

    html.Div(
            [
                html.Div(
                    [
                        html.P('Select State:', style={'font-size':font_title_above_drop_down, 'margin-bottom':'5px'}),
                        dcc.Dropdown(id="select_country",
                        options=[{'label': country, 'value': country} for country in orderedState],
                        multi=False,
                        value="California",
                        clearable=False,
                        style = {'width': "100%", 'font-size':font_drop_down__size},),
                    ],
                    style={'margin-left':'7px', 'margin-top': '10', 'display':'inline-block', 'width':'200px'}
                ),
                html.Div(
                    [
                        html.P('Compared To', style={'font-size': font_title_above_drop_down, 'font-family':'arial', 'margin-bottom':'0px' }),
                    ],
                    style={'margin-left': '30px', 'margin-top': '10', 'display': 'inline-block', 'width': 'auto', 'vertical-align':'bottom',
                                                     'margin-bottom':'5px', 'margin-right':'30px'}
                ),

                html.Div(
                    [
                        html.P('Select State:', style={'font-size': font_title_above_drop_down, 'margin-bottom': '5px'}),
                        dcc.Dropdown(id="select_country2",
                                     options=[{'label': country, 'value': country} for country in orderedState],
                                     multi=False,
                                     value="Arizona",
                                     clearable=False,
                                     style={'width': "100%", 'font-size': font_drop_down__size}, ),
                    ],
                    style={'margin-top': '10', 'display': 'inline-block', 'width': '200px'}
                ),
            ],
        ),


    html.Div([
    dcc.Graph(id='covid_map2', figure={}, style={"border": "2px lightgrey solid", "border-radius":'4px', 'height': 170, 'width':'100%', 'margin-top':'10px'},
              config={
                  'displayModeBar': False
              },
              ),
    dcc.Graph(id='covid_map3', figure={},style={"border": "2px lightgrey solid", "border-radius": '4px', 'height': 170, 'width': '100%', 'margin-top': '9px', 'margin-bottom':'9px'},
              config={
                  'displayModeBar': False
              },
              )
    ], style={'display':'inline-block', 'margin-left':'7px','width':'42%' }),


    dcc.Graph(id='covid_map', figure={},style={"border": "2px lightgrey solid", "border-radius": '4px',  'height': '540px', 'width': '55%','display': 'inline-block', 'float': 'right', 'margin-top':'10px' ,'margin-right':'20px'},
              config={
                  'displayModeBar': False
              },
              ),

    html.Div(dcc.Graph(id='totalGraph', figure={}, style={"border": "2px lightgrey solid", "border-radius": '4px', 'height': 170},
                       config={
                           'displayModeBar': False
                       },
                       ), style={'display':'inline-block', 'margin-left':'7px', 'width':'42%'}),
    html.Br()

])

@app.callback(
    [Output(component_id='covid_map2', component_property='figure'),
     Output(component_id='covid_map3', component_property='figure'),
     Output(component_id='covid_map', component_property='figure'),
     Output(component_id='totalGraph', component_property='figure'),
     Output(component_id='output_container', component_property='children')],
    [Input(component_id='select_country', component_property='value'),
    Input(component_id='select_country2', component_property='value')],
)
def update_graph(selected_country, selected_country2):

    global subTitle
    global last_day_updated

    #yesterday represents last time date was updated
    yesterdayString = dt.strptime(str(last_day_updated), "%Y-%m-%d").strftime("%m-%d-%Y")
    yesterdayStringConverted = dt.strptime(yesterdayString, "%m-%d-%Y")
    yesterdayStringMonth = calendar.month_name[yesterdayStringConverted.month]
    yesterdayStringDay = yesterdayStringConverted.day
    yesterdayStringYear = yesterdayStringConverted.year

    today = datetime.date.today()
    todayString = dt.strptime(str(today), "%Y-%m-%d").strftime("%m-%d-%Y")
    todayStringConverted = dt.strptime(todayString, "%m-%d-%Y")
    todayStringMonth = calendar.month_name[todayStringConverted.month]
    todayStringDay = todayStringConverted.day
    todayStringYear = todayStringConverted.year

    if(todayStringMonth != yesterdayStringMonth or (todayStringDay != yesterdayStringDay) or (todayStringYear!= yesterdayStringYear)):
        #call api requests and update data
        global df
        df = dfStateTotalsRequest()
        global df6
        df6 = dfStateAgeGroupRequest()
        global df_final
        df_final = transformTotalStateDF(df)
        global df_states
        df_states = onlyUSStates(df_final)

        subTitle = getSource() + getLastTime(df_states)
        global state_dic
        state_dic = dicConfirmedDeathsStates(df_states)

        last_day_updated = datetime.date.today()


    dff = df6.copy()

    dff2 = dff.loc[(dff["state"] == selected_country)]  #state 1
    dff2 = dff2.groupby(['age_group']).agg({'covid_19_deaths': 'sum'})

    dff3 = dff.loc[(dff["state"] == selected_country2)] #state2
    dff3 = dff3.groupby(['age_group']).agg({'covid_19_deaths': 'sum'})

    xVals = []
    yVals = []
    zeroTo4 = 0
    state_dic_1 = {}
    for index, row in dff2.iterrows():          #go through each age group for selected state
        holdAgeGroup = index.split('year')      #remove text after the age group range
        if holdAgeGroup[0].strip() == "85":
            xVals.append(holdAgeGroup[0])
        else:
            if(holdAgeGroup[0].strip()=="1-4" or holdAgeGroup[0].strip()=="Under 1"):   #group both age groups
                zeroTo4+=row[0]
            else:
                xVals.append(holdAgeGroup[0])
        if not (holdAgeGroup[0].strip()=="1-4" or holdAgeGroup[0].strip()=="Under 1"):
            yVals.append(row[0])
            state_dic_1[holdAgeGroup[0]] = row[0]
    xVals.append("0-4") #add grouped age groups into corresponding lists
    yVals.append(zeroTo4)
    state_dic_1["0-4"] = zeroTo4

    hold = sorted(state_dic_1.items(), key=lambda t: int(t[0].split('-')[0]))  #sort age groups
    xVals = []
    yVals = []
    for item in hold:           #add age groups and their counts in corresponding lists
        if item[0] == '85':     #manually append plus sign at end of 85 age for x-axis
            xVals.append('85+')
        else:
            xVals.append(item[0])
        yVals.append(item[1])


    x = xVals
    if len(dff2) != 0:
        y = yVals
    else:
        y = [0, 0, 0]

    #repeat same thing as above for second selected state
    xVals2 = []
    yVals2 = []
    zeroTo4_2 = 0
    state_dic_2 = {}
    for index, row in dff3.iterrows():
        holdAgeGroup = index.split('year')
        if holdAgeGroup[0].strip() == "85":
            xVals2.append(holdAgeGroup[0])
        else:
            if (holdAgeGroup[0].strip() == "1-4" or holdAgeGroup[0].strip() == "Under 1"):
                zeroTo4_2 += row[0]
            else:
                xVals2.append(holdAgeGroup[0])
        if not (holdAgeGroup[0].strip() == "1-4" or holdAgeGroup[0].strip() == "Under 1"):
            state_dic_2[holdAgeGroup[0]] = row[0]
            yVals2.append(row[0])

    #under 1 and 1-4 age groups merged together
    xVals.append("0-4")
    yVals.append(zeroTo4_2)
    state_dic_2["0-4"] = zeroTo4_2

    hold = sorted(state_dic_2.items(), key=lambda t: int(t[0].split('-')[0]))
    xVals2 = []
    yVals2 = []
    for item in hold:
        if item[0] == '85':
            xVals2.append('85+')
        else:
            xVals2.append(item[0])
        yVals2.append(item[1])

    x2 = xVals2
    if len(dff3) != 0:
        y2 = yVals2
    else:
        y2 = [0, 0, 0]

    colors = ['#19D3F3']*12  #color for bar 1
    colors2 = ['#ff7f0e']*12 #color for bar 2

    state1 = state_dic[selected_country]  #state_dic contains confirmed and death counts
    state2 = state_dic[selected_country2]

    x.append("Unknown")             #contains counts for cases without an age group specified
    if(state1[1] < sum(yVals)):
        y.append(0)
    else:
        y.append(state1[1] - sum(yVals))

    x2.append("Unknown")
    if(state2[1] < sum(yVals2)):
        y2.append(0)
    else:
        y2.append(state2[1] - sum(yVals2))

    #create graph for age groups and cases
    fig = go.Figure(
        data=[go.Bar(
        x=x,
        y=y,
        textposition='auto',
        name=selected_country,
        marker_color=colors, # marker color can be a single color value or an iterable
        ),

        go.Bar(
            x=x2,
            y=y2,
            name=selected_country2,
            textposition='auto',
            marker_color=colors2,  # marker color can be a single color value or an iterable
        )]
    )


    fig.update_layout(
        yaxis={
            'title': "Death Count",
        },
        xaxis={
            'title': "Age Group",
        },
        title ={'text':"COVID-19 Deaths by Age Group State Comparison", 'xanchor':'center', 'x':.5}
        ,
        margin=dict(
            l=0,
            r=0,
            b=0,
            t=50,
        ),
    )

    fRate = round((float(sum(yVals)/state1[0])*100), 1) #fatality rate for first statte based on age group
    #fig_state_1 is dashbboard for first state
    fig_state_1 = make_subplots(
        rows = 1, cols = 3,
        specs=[
                [{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}],

        ],
    )
    fig_state_1.add_trace(
        go.Indicator(
            mode="number",
            value=state1[0],
            title={'text':"Confirmed",'font': {'size': font_size_text}},
            number={'font': {'color':'green', 'size': font_size_nums}},
        ),
        row = 1, col = 1
    )
    fig_state_1.add_trace(
        go.Indicator(
            mode="number",
            value=sum(yVals),
            title={'text':"Deaths",'font': {'size': font_size_text}},
            number={'font': {'size': font_size_nums, 'color':'red'}},
        ),
        row = 1, col = 2
    )

    fig_state_1.add_trace(
        go.Indicator(
            mode="number",
            value=fRate,
            title={'text':"Fatality Rate",'font': {'size': font_size_text}},
            number={'suffix': "%", 'font': {'size': font_size_nums, 'color':'#0099C6'}},
        ),
        row = 1, col = 3
    )

    fig_state_2 = make_subplots(
        rows = 1, cols = 3,
        specs=[
                [{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}],

        ]
    )
    fig_state_2.add_trace(
        go.Indicator(
            mode="number",
            value=state2[0],
            title={'text':"Confirmed",'font': {'size': font_size_text}},
            number={'font': {'color':'green', 'size': font_size_nums}},
        ),
        row = 1, col = 1
    )

    fig_state_2.add_trace(
        go.Indicator(
            mode="number",
            value=sum(yVals2),
            title={'text':"Deaths",'font': {'size': font_size_text}},
            number={'font': {'size': font_size_nums, 'color':'red'}},
        ),
        row = 1, col = 2
    )

    fRate2 = round((float(sum(yVals2)/state2[0])*100), 1) #fatality rate for first statte based on age group
    fig_state_2.add_trace(
        go.Indicator(
            mode="number",
            value=fRate2,
            title={'text':"Fatality Rate",'font': {'size': font_size_text}},
            number={'suffix': "%", 'font': {'size': font_size_nums, 'color':'#0099C6'}},
        ),
        row = 1, col = 3
    )

    fig_state_1.update_layout(
        title={'text':"<b>"+selected_country + " Overview<b>", 'font':{'size': stateTitleSize}},
        margin= margin_dic
    ),

    fig_state_2.update_layout(
        title={'text':"<b>" + selected_country2 + " Overview<b>", 'font':{'family': 'Helvetica', 'size': stateTitleSize}},
        margin=margin_dic
    ),

    # USA totals
    TotalConfirmedUSA = df_states["Confirmed"].sum()
    TotalDeadUSA = df_states["Deaths"].sum()
    totalFRate = round((float(TotalDeadUSA / TotalConfirmedUSA) * 100), 1)

    # dashboard for USA totals containing confirmed and death counts
    figTotal = make_subplots(
        rows=1, cols=3,
        specs=[
            [{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}],
        ]
    )

    # dashboard for total counts in the country
    figTotal.add_trace(
        go.Indicator(
            mode="number",
            value=TotalConfirmedUSA,
            title={'text': "Confirmed", 'font': {'size': font_size_text}},
            number={'font': {'color': 'green', 'size': font_size_nums}},
        ),
        row=1, col=1
    )
    figTotal.add_trace(
        go.Indicator(
            mode="number",
            value=TotalDeadUSA,
            title={'text': "Deaths", 'font': {'size': font_size_text}},
            number={'font': {'size': font_size_nums, 'color': 'red'}},
        ),
        row=1, col=2
    )
    figTotal.add_trace(
        go.Indicator(
            mode="number",
            value=totalFRate,
            title={'text': "Fatality Rate", 'font': {'size': font_size_text}},
            number={'suffix': "%", 'font': {'size': font_size_nums, 'color': '#0099C6'}},
        ),
        row=1, col=3
    )

    figTotal.update_layout(
        title={'text': "<b>United States" + " Overview<b>", 'font': {'family': 'Helvetica', 'size': stateTitleSize}},
        margin=margin_dic
    ),

    container = subTitle
    return fig_state_1, fig_state_2, fig, figTotal, container


# ------------------------------------------------------------------------------

