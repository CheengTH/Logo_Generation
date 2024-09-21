from openai import OpenAI
import streamlit as st
import PIL.Image
import json
import io
import base64
import requests


from IPython.display import display, Image

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Functions part
def image_gen(img):
    response = client.images.generate(
        model = "dall-e-2",
        prompt = "combine the items in art style simple geometrical shapes on a white background: " + img +
            ". Do not include any text, words, letters, or alphabets in the image. "
            "Focus solely on the portrait and the specified elements, with no additional variations.",
        size = "256x256",
        n = 1,
    )
    return response.data[0].url

def vision_assistant(img):
    response = client.chat.completions.create(
        model = "gpt-4o-mini",
        messages= [{
            "role":"user",
            "content": [{
                "type" : "text",
                "text" : """describe the appearance features as elements and as accurate and as descriptive as possible. 
                Each description cannot exceed five words. 
                Give at least 3 features.
                Show in json form. Do not mention json.
                It should contain the following:
                - gender
                - wearings
                - hair/hat
                - face features
                """
            },
            # {
            #     "type" : "image_url",
            #     "image_url" : {"url" : "https://cdn.pixabay.com/photo/2023/11/10/02/30/woman-8378634_1280.jpg"}
            # }],
            # "role":"assistant",
            # "content": [{
            #     "type" : "text",
            #     "text" : """{
            #                 "wearings": "black top, patterned scarf",
            #                 "face features": "curly hair, defined eyebrows, brown eyes, full lips, smooth skin"
            #                 }"""
            # }],
            # "role":"user",
            # "content": [{
            #     "type" : "text",
            #     "text" :  """Describe this with the same json format.
            #                 Do not mention json.
            #                 It should contain the following:
            #                 - wearings
            #                 - face features"""
            # },
            {
                "type" : "image_url",
                "image_url": {"url": "data:image/png;base64," + base64.b64encode(img.getvalue()).decode()}
            }]
        }]
    )
    return response.choices[0].message.content

def extract_strings(obj):
    strings = []
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            strings.extend(extract_strings(value))
    
    elif isinstance(obj, list):
        for item in obj:
            strings.extend(extract_strings(item))
    
    elif isinstance(obj, str):
        strings.append(obj)
    
    return strings

def reducer(input):
    if isinstance(input, list):
        input = ", ".join(input) 
    elif not isinstance(input, str):
        input = str(input)
    response = client.chat.completions.create(
        model = 'gpt-4o-mini',
        messages = [
            {'role':'system','content':"""
            You are a logo designer assistant. Your customer gives you a list of elements.
            Remove the elements that are not suitable to create a simplified logo for a portrait.
            Remove just color descriptions too since the logo should be only black and white.
            The result should remain as list. Do not mention list.
            """},
            {'role':'user','content':input}
        ]
    )
    return response.choices[0].message.content

def explainer(img, elements):
    response = client.chat.completions.create(
        model = "gpt-4o-mini",
        messages= [{
            "role":"user",
            "content": [{
                "type" : "text",
                "text" : """
                You are a logo designer assistant. You created a logo based on these elements: 
                """
                + elements +
                """
                . Do not describe anything that are not in the elements.
                describe this logo with the elements you used:
                """
            },
            {
                "type" : "image_url",
                "image_url": {"url":img}
            }]
        }]
    )
    return response.choices[0].message.content

def clear_session_state():
    for key in st.session_state.keys():
        del st.session_state[key]
    st.session_state.clear()     
    st.cache_data.clear()
    uploaded_file = None
    st.rerun()

# Execution part

st.title("Portrait Logo Generator")
uploaded_file = st.file_uploader("Choose your portrait image file", type=["jpg","jpeg","png+"])

if uploaded_file is not None:
    
    img = PIL.Image.open(uploaded_file)
    st.image(img, caption='Uploaded Image', use_column_width=True)
    
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)

    description = vision_assistant(img_byte_arr)
    # st.write(description)
    data = json.loads(description)
    # st.write(data)

    string_values = extract_strings(data)
    # reduced_options = reducer(string_values)
    
    if 'reduced_options' not in st.session_state:
        st.session_state.reduced_options = string_values

    st.write("Here are the elements our assistant found: ")

    selection_options = string_values #[item.strip() for item in string_values.split(',')]

    if 'selected_items' not in st.session_state:
        st.session_state.selected_items = []
        
    with st.form(key='selection_form'):
        
        for option in st.session_state.reduced_options:
            if st.checkbox(option.strip(), value=option.strip() in st.session_state.selected_items):
                if option.strip() not in st.session_state.selected_items:
                    st.session_state.selected_items.append(option.strip())
            else:
                if option.strip() in st.session_state.selected_items:
                    st.session_state.selected_items.remove(option.strip())

        if st.form_submit_button(label='Submit'):
            url = image_gen(str(st.session_state.selected_items))
            st.image(url, caption='Generated Logo', use_column_width=True)
            explanation = explainer(url, str(st.session_state.selected_items))
            st.write(explanation)
            
            image_response = requests.get(url)
            img = PIL.Image.open(io.BytesIO(image_response.content))
            
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0) 
            
            st.session_state.generated_image = img_byte_arr

            
if 'generated_image' in st.session_state:
    st.download_button(
        label="Download Generated Logo",
        data=st.session_state.generated_image,
        file_name="generated_logo.png",
        mime="image/png"
    )

if st.button("Clear Session"):
    clear_session_state()