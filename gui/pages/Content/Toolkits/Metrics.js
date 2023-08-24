import React, {useState, useEffect, useRef} from 'react';
import {ToastContainer, toast} from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import {
 getApiKeys,
} from "@/pages/api/DashboardService";
import {
  loadingTextEffect,
} from "@/utils/utils";

export default function Metrics() {
  const [apiKeys, setApiKeys] = useState([]);
  const [totalTokens, setTotalTokens] = useState(0)
  const [totalAgentsUsing, setTotalAgentsUsing] = useState(0)
  const [totalCalls, setTotalCalls] = useState(0)
  const [callLogs, setCallLogs] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [loadingText, setLoadingText] = useState("Loading Metrics");
  const metricsData = [
    { label: 'Total Calls', value: totalCalls },
    { label: 'Total Tokens Consumed', value: totalTokens },
    { label: 'Total Agents Using', value: totalAgentsUsing }
  ];

  useEffect(() => {
    loadingTextEffect('Loading Metrics', setLoadingText, 500);
    fetchApiKeys()
  }, []);

  const fetchApiKeys = () => {
    getApiKeys()
      .then((response) => {
        const formattedData = response.data.map(item => {
          return {
            ...item,
            created_at: `${new Date(item.created_at).getDate()}-${["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"][new Date(item.created_at).getMonth()]}-${new Date(item.created_at).getFullYear()}`
          };
        });
        setApiKeys(formattedData)
        setIsLoading(false)
      })
      .catch((error) => {
        console.error('Error fetching Metrics', error);
      });
  }

  return (<>
    <div className="row">
      <div className="col-12 padding_5 ">
        {!isLoading ?
          <div>
            <div style={{display: "flex", gap: '5px'}}>
            {metricsData.map((metric, index) => (
              <div className="display_column_container" key={index}>
                <span className="text_14">{metric.label}</span>
                <div className="text_60_bold display_flex justify_center align_center w_100 h_100 mb_24">
                  {metric.value}
                </div>
              </div>
            ))}
            </div>
              <div className="display_column_container mt_5">
                <span className="text_14">Call Logs</span>
                <div className="scrollable_container table_container" style={{background: 'none'}}>
                  <table className="w_100 margin_0 padding_0">
                    <thead>
                    <tr className="border_top_none text_align_left" style={{borderBottom: 'none'}}>
                      <th className="table_header w_15">Longest Timestamp</th>
                      <th className="table_header w_15">Agent Name</th>
                      <th className="table_header w_40">Run Name</th>
                      <th className="table_header w_15">Model</th>
                      <th className="table_header w_15">Tokens Used</th>
                    </tr>
                    </thead>
                  </table>
                  <div className="overflow_auto w_100">
                    <table className="table_css margin_0">
                      <tbody>
                      {apiKeys.map((item, index) => (
                        <tr key={index} className="text_align_left">
                          <td className="table_data w_15 border_gray border_left_none">{item.created_at}</td>
                          <td className="table_data w_15 border_gray">{item.name}</td>
                          <td className="table_data w_40 border_gray">{item.name}</td>
                          <td className="table_data w_15 border_gray">{item.name}</td>
                          <td className="table_data w_15 border_gray">34</td>
                        </tr>
                      ))}
                      </tbody>
                    </table>
                  </div>
                </div>
          </div>
          </div>
          :  <div className="loading_container">
          <div className="signInInfo loading_text">{loadingText}</div>
        </div>}
      </div>
    </div>
    <ToastContainer/>
  </>)
}